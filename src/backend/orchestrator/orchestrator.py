"""Central orchestrator — coordination of pipeline stages.

Responsibilities (see plan §1, §3, §5):
  * Own the StateStore (single writer).
  * Own the WorkerManager (lifecycle of agent processes).
  * Drain every stage's output queue, update the StateStore, and forward
    the chunk to the next stage's input queue.
  * Maintain in-memory `project_state` and `pipeline_state` for the
    FastAPI layer to query (cheap, no need to hit the DB on every GUI poll).
  * Surface progress / errors / HITL requests to subscribers — in
    production this is the WebSocket fanout; for Phase 1 it is a
    thread-safe callback registry.
  * Pause / resume / stop the whole pipeline or individual stages.

Design notes
------------
  * The orchestrator runs in the FastAPI process. It is a single
    asyncio-free event loop, driven by a background thread that does
    blocking queue.get() with a short timeout. FastAPI handlers run on
    their own threadpool and call into the orchestrator through a
    `threading.RLock` where needed.
  * Agents never talk to the StateStore directly. They receive
    `{chunk_id, action}` tasks and emit `{type, chunk_id, payload}`
    responses. The orchestrator translates those to DB reads/writes
    and to forwarding messages.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from .pipeline import (
    ALL_STAGES,
    ASSEMBLER,
    DEFAULT_PIPELINE_ORDER,
    PARALLELIZABLE_STAGES,
    STAGE_TO_STATUS,
    STATUS_ERROR,
    StageSpec,
    build_stages,
)
from .state_store import StateStore
from .worker_manager import WorkerManager

logger = logging.getLogger(__name__)


# Callback signature for state changes (used by the WebSocket layer).
StateListener = Callable[[dict[str, Any]], None]


@dataclass
class ProjectContext:
    """All per-project state held in memory by the orchestrator."""

    project_id: str
    project_dir: Path
    source_lang: str
    target_lang: str
    source_path: Path
    output_path: Path | None = None
    started_at: float = field(default_factory=time.time)
    status: str = "idle"  # idle | running | paused | stopped | done | error


class Orchestrator:
    """The brain of the v4 backend.

    Typical lifecycle:

        store = StateStore(db_path, vector_dir=...)
        orch = Orchestrator(store)
        orch.start(project=ProjectContext(...))
        ...
        orch.stop()
        orch.shutdown()
    """

    def __init__(self, store: StateStore):
        self.store = store
        self._stages: dict[str, StageSpec] = build_stages()
        self._workers = WorkerManager(self._stages)
        self._workers.set_exit_hook(self._on_worker_exit)

        self._lock = threading.RLock()
        self._project: ProjectContext | None = None
        self._drain_thread: threading.Thread | None = None
        self._stop_drain = threading.Event()
        self._listeners: list[StateListener] = []
        self._event_log: deque[dict[str, Any]] = deque(maxlen=500)
        self._pending_hltl: dict[str, dict[str, Any]] = {}
        self._paused_stages: set[str] = set()

    # ---------- project lifecycle ----------

    def start(self, project: ProjectContext) -> None:
        with self._lock:
            if self._project is not None and self._project.status in (
                "running",
                "paused",
            ):
                raise RuntimeError(
                    f"Pipeline already running for project {self._project.project_id!r}"
                )
            self._project = project
            project.status = "running"
            self.store.clear_project_data()
            self.store.set_state(
                "current_project",
                {
                    "project_id": project.project_id,
                    "project_dir": str(project.project_dir),
                    "source_lang": project.source_lang,
                    "target_lang": project.target_lang,
                    "source_path": str(project.source_path),
                    "output_path": str(project.output_path) if project.output_path else None,
                    "started_at": project.started_at,
                },
            )

        for stage in ALL_STAGES:
            self._workers.start_stage(stage)
        self._stop_drain.clear()
        if self._drain_thread is None or not self._drain_thread.is_alive():
            self._drain_thread = threading.Thread(
                target=self._drain_loop, name="orch-drain", daemon=True
            )
            self._drain_thread.start()
        from ..agents.base_worker import make_task_message

        self._workers.queues_for("parser").input.put(
            make_task_message(
                chunk_id=project.project_id,
                action="parse",
                payload={
                    "project_id": project.project_id,
                    "project_dir": str(project.project_dir),
                    "source_path": str(project.source_path),
                    "source_lang": project.source_lang,
                    "target_lang": project.target_lang,
                    "output_path": str(project.output_path) if project.output_path else None,
                },
            )
        )
        self._emit(
            {
                "type": "pipeline_started",
                "project_id": project.project_id,
                "timestamp": _now_iso(),
            }
        )

    def pause(self) -> None:
        with self._lock:
            if self._project is None:
                return
            self._project.status = "paused"
            for stage in ALL_STAGES:
                self._workers.pause_stage(stage)
                self._paused_stages.add(stage)
        self._emit({"type": "pipeline_paused", "timestamp": _now_iso()})

    def resume(self) -> None:
        with self._lock:
            if self._project is None:
                return
            self._project.status = "running"
            for stage in self._paused_stages:
                self._workers.resume_stage(stage)
            self._paused_stages.clear()
        self._emit({"type": "pipeline_resumed", "timestamp": _now_iso()})

    def stop(self) -> None:
        with self._lock:
            if self._project is None:
                return
            self._project.status = "stopped"
            for stage in ALL_STAGES:
                self._workers.shutdown_stage(stage)
        self._emit({"type": "pipeline_stopped", "timestamp": _now_iso()})

    def shutdown(self) -> None:
        """Tear down the orchestrator (stops all workers)."""
        self._stop_drain.set()
        if self._drain_thread is not None:
            self._drain_thread.join(timeout=2.0)
        self._workers.shutdown()
        with self._lock:
            self._project = None
        self._emit({"type": "pipeline_shutdown", "timestamp": _now_iso()})

    # ---------- chunk submission ----------

    def submit_chunks(self, chunks: Iterable[dict[str, Any]]) -> int:
        """Inject a batch of parsed chunks into the Parser output channel.

        The Parser worker (Agent 1) is the entry point of the pipeline;
        its input is `parser_in`. In Phase 1, when the Parser agent
        itself is not yet implemented, the orchestrator can act as a
        proxy by writing the chunks into the store and pushing one
        task per chunk to the FastTranslator queue.
        """
        spec = self._stages[FAST_TRANSLATOR := "fast_translator"]
        q = self._workers.queues_for(spec.key).input
        count = 0
        for chunk in chunks:
            chunk_id = chunk.get("id") or uuid.uuid4().hex
            chunk.setdefault("id", chunk_id)
            self.store.add_chunk(chunk)
            self.store.update_chunk_field(chunk_id, "status", "parsed")
            from ..agents.base_worker import make_task_message

            # The orchestrator is the single reader of the StateStore;
            # we pre-fetch the source text so the agent never has to.
            stored = self.store.get_chunk(chunk_id) or {}
            source_text = chunk.get("source_text") or stored.get("source_text", "")
            q.put(
                make_task_message(
                    chunk_id=chunk_id,
                    action="translate",
                    payload={
                        "chapter_id": chunk.get("chapter_id") or stored.get("chapter_id"),
                        "chapter_title": chunk.get("chapter_title")
                        or stored.get("chapter_title"),
                        "source_text": source_text,
                        "neighbor_chars": 300,
                    },
                )
            )
            count += 1
        self._emit(
            {
                "type": "chunks_submitted",
                "count": count,
                "timestamp": _now_iso(),
            }
        )
        return count

    # ---------- HITL ----------

    def register_hltl(self, msg: dict[str, Any]) -> None:
        """Record a human-in-the-loop request emitted by an agent."""
        chunk_id = msg.get("chunk_id")
        if not chunk_id:
            return
        issue = (msg.get("payload") or {}).get("issue", {})
        request_id = uuid.uuid4().hex
        record = {
            "request_id": request_id,
            "chunk_id": chunk_id,
            "stage": msg.get("stage"),
            "issue": issue,
            "received_at": _now_iso(),
        }
        with self._lock:
            self._pending_hltl[request_id] = record
            self.store.update_chunk_field(chunk_id, "status", "waiting_for_human")
        self._emit(
            {
                "type": "hltl_alert",
                "request_id": request_id,
                "chunk_id": chunk_id,
                "stage": msg.get("stage"),
                "issue": issue,
                "timestamp": _now_iso(),
            }
        )

    def respond_hltl(self, request_id: str, answer: str) -> bool:
        """Apply a human answer to a pending HITL request.

        Phase 1: store the answer, mark the chunk back to its last
        known good status, and re-inject the chunk into the next
        stage. The full UX (StageAware re-injection) lands in Phase 8.
        """
        with self._lock:
            record = self._pending_hltl.pop(request_id, None)
        if record is None:
            return False
        chunk_id = record["chunk_id"]
        self.store.set_state(
            f"hltl_response:{request_id}",
            {
                "answer": answer,
                "chunk_id": chunk_id,
                "responded_at": _now_iso(),
            },
        )
        # Best-effort: send the chunk back to the requesting stage.
        target_stage = record.get("stage")
        if target_stage and target_stage in self._stages:
            q = self._workers.queues_for(target_stage).input
            from ..agents.base_worker import make_task_message

            q.put(
                make_task_message(
                    chunk_id=chunk_id,
                    action="hltl_reprocess",
                    payload={"answer": answer, "issue": record.get("issue")},
                )
            )
        self.store.update_chunk_field(chunk_id, "status", "parsed")
        self._emit(
            {
                "type": "hltl_resolved",
                "request_id": request_id,
                "chunk_id": chunk_id,
                "answer": answer,
                "timestamp": _now_iso(),
            }
        )
        return True

    def pending_hltl(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(r) for r in self._pending_hltl.values()]

    # ---------- listeners (WebSocket fanout stub) ----------

    def add_listener(self, listener: StateListener) -> None:
        with self._lock:
            self._listeners.append(listener)

    def remove_listener(self, listener: StateListener) -> None:
        with self._lock:
            try:
                self._listeners.remove(listener)
            except ValueError:
                pass

    def _emit(self, event: dict[str, Any]) -> None:
        event.setdefault("timestamp", _now_iso())
        with self._lock:
            self._event_log.append(event)
            listeners = list(self._listeners)
        for cb in listeners:
            try:
                cb(event)
            except Exception:
                logger.exception("Listener raised; dropping event %s", event.get("type"))

    # ---------- query ----------

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            project = self._project
        return {
            "project": (
                {
                    "project_id": project.project_id,
                    "status": project.status,
                    "source_lang": project.source_lang,
                    "target_lang": project.target_lang,
                    "started_at": project.started_at,
                }
                if project is not None
                else None
            ),
            "state_store": self.store.snapshot(),
            "workers": self._workers.snapshot(),
            "paused_stages": sorted(self._paused_stages),
            "pending_hltl": len(self._pending_hltl),
            "event_log_tail": list(self._event_log)[-20:],
            "output_artifact": self.store.get_state_json("output_artifact"),
            "project_manifest_path": self.store.get_state("project_manifest_path"),
        }

    def recent_events(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._event_log)[-limit:]

    # ---------- internals: drain loop ----------

    def _drain_loop(self) -> None:
        """Read every stage's output queue, update the store, forward chunks.

        We round-robin across stages to avoid starving any one of them.
        Each iteration we do a short blocking get on each queue, in
        pipeline order, and process whatever message is there.
        """
        while not self._stop_drain.is_set():
            did_work = False
            for stage in DEFAULT_PIPELINE_ORDER:
                if stage not in self._stages:
                    continue
                try:
                    q = self._workers.queues_for(stage).output
                except KeyError:
                    continue
                try:
                    msg = q.get_nowait()
                except Exception:
                    continue
                did_work = True
                self._handle_worker_message(stage, msg)
            if not did_work:
                time.sleep(0.05)

    def _handle_worker_message(self, stage: str, msg: dict[str, Any]) -> None:
        msg_type = msg.get("type")
        chunk_id = msg.get("chunk_id")
        payload = msg.get("payload") or {}

        if msg_type == "error":
            logger.error(
                "[%s] error on chunk %s: %s",
                stage,
                chunk_id,
                payload.get("message"),
            )
            if chunk_id:
                self.store.update_chunk_field(chunk_id, "status", STATUS_ERROR)
                self.store.update_chunk_field(
                    chunk_id, "error_message", payload.get("message")
                )
            self._emit(
                {
                    "type": "agent_error",
                    "stage": stage,
                    "chunk_id": chunk_id,
                    "payload": payload,
                }
            )
            return

        if msg_type == "hltl_request":
            self.register_hltl(msg)
            return

        if msg_type == "progress":
            base = {
                "stage": stage,
                "chunk_id": chunk_id,
                "percent": payload.get("percent"),
                "note": payload.get("note"),
            }
            self._emit({"type": "agent_progress", **base})
            self._emit({"type": "stage_progress", **base})
            if chunk_id:
                self._emit({"type": "chunk_progress", **base})
            return

        if msg_type == "done":
            # Parser emits a stage-level done with chunk_id=None and a
            # list of chapters/chunks in the payload. We need to inject
            # those into the FastTranslator queue here, because the
            # parser's terminal=True prevents the regular forward path
            # from doing it.
            if stage == "parser" and chunk_id is None:
                if payload.get("manifest_path"):
                    self.store.set_state("project_manifest_path", payload["manifest_path"])
                if payload.get("target_path"):
                    self.store.set_state("target_path", payload["target_path"])
                chapters = payload.get("chapters") or []
                flat: list[dict[str, Any]] = []
                for chap in chapters:
                    for c in chap.get("chunks") or []:
                        c.setdefault("chapter_id", chap.get("id"))
                        c.setdefault("chapter_title", chap.get("title"))
                        flat.append(c)
                if flat:
                    self.submit_chunks(flat)
                self._emit(
                    {
                        "type": "agent_done",
                        "stage": stage,
                        "chunk_id": None,
                        "payload": payload,
                    }
                )
                self._emit(
                    {
                        "type": "log",
                        "message": (
                            f"parser: {payload.get('chunk_count', 0)} chunks "
                            f"extracted; manifest={payload.get('manifest_path', '')}"
                        ),
                    }
                )
                return
            # LexiconBuilder emits terms in its payload. We persist
            # them and forward the chunk to the next stage.
            if stage == "lexicon_builder" and payload.get("terms"):
                for term in payload.get("terms") or []:
                    if isinstance(term, dict) and "id" in term:
                        try:
                            self.store.add_lexicon_term(term)
                        except Exception:
                            logger.exception("lexicon: failed to persist term")
            # GrammarProofer emits a list of issues; persist them so
            # the GUI chunk detail can show them.
            if stage == "grammar_proofer" and chunk_id and payload.get("grammar_issues"):
                import uuid as _uuid

                for issue in payload.get("grammar_issues") or []:
                    if not isinstance(issue, dict):
                        continue
                    try:
                        self.store.add_grammar_issue(
                            {
                                "id": _uuid.uuid4().hex[:12],
                                "chunk_id": chunk_id,
                                "start_pos": issue.get("start_pos"),
                                "end_pos": issue.get("end_pos"),
                                "message": issue.get("message", ""),
                                "suggestion": issue.get("suggestion"),
                                "applied": bool(issue.get("applied")),
                                "rule_id": issue.get("rule_id"),
                            }
                        )
                    except Exception:
                        logger.exception("grammar: failed to persist issue")
            # QAValidator emits issues, too.
            if stage == "qa_validator" and chunk_id and payload.get("qa_issues"):
                import uuid as _uuid

                for issue in payload.get("qa_issues") or []:
                    if not isinstance(issue, dict):
                        continue
                    try:
                        self.store.add_qa_issue(
                            {
                                "id": _uuid.uuid4().hex[:12],
                                "chunk_id": chunk_id,
                                "issue_type": issue.get("priority", "REGISTER"),
                                "severity": (
                                    "high"
                                    if issue.get("priority") in ("FABRICATION", "OMISSION")
                                    else "medium"
                                ),
                                "message": issue.get("explanation", ""),
                                "auto_fixed": bool(issue.get("auto_fix")),
                            }
                        )
                    except Exception:
                        logger.exception("qa: failed to persist issue")
            # ConsistencyChecker emits flags.
            if stage == "consistency_checker" and chunk_id and payload.get("consistency_flags"):
                import uuid as _uuid

                for flag in payload.get("consistency_flags") or []:
                    if not isinstance(flag, dict):
                        continue
                    try:
                        self.store.add_consistency_flag(
                            {
                                "id": _uuid.uuid4().hex[:12],
                                "chunk_id": chunk_id,
                                "source_term": flag.get("source_term"),
                                "expected_translation": flag.get("expected_translation"),
                                "found_translation": flag.get("found_translation"),
                                "confidence": float(flag.get("confidence", 0.0) or 0.0),
                                "resolved": False,
                            }
                        )
                    except Exception:
                        logger.exception("consistency: failed to persist flag")
            self._on_stage_done(stage, chunk_id, payload)
            return

        logger.debug("Unhandled message from %s: %r", stage, msg)

    def _on_stage_done(
        self, stage: str, chunk_id: str | None, payload: dict[str, Any]
    ) -> None:
        if not chunk_id:
            return
        if stage == ASSEMBLER:
            if payload.get("output_path"):
                artifact = {
                    "output_path": payload.get("output_path"),
                    "chunk_count": payload.get("chunk_count", 0),
                    "created_at": _now_iso(),
                }
                self.store.set_state("output_artifact", artifact)
                with self._lock:
                    if self._project is not None:
                        self._project.status = "done"
                self._emit({"type": "artifact_ready", **artifact})
        # 1. Persist any data the stage produced.
        for field_name in (
            "raw_translation",
            "glossary_applied",
            "qa_checked",
            "grammar_checked",
            "polished_translation",
        ):
            if field_name in payload:
                self.store.update_chunk_field(chunk_id, field_name, payload[field_name])
        new_status = payload.get("status") or STAGE_TO_STATUS.get(stage, "parsed")
        self.store.update_chunk_field(chunk_id, "status", new_status)

        # 2. Forward to the next stage (unless the stage signals "no
        #    further processing" via payload["terminal"] = True).
        if not payload.get("terminal"):
            next_stage = self._next_stage(stage)
            if next_stage == ASSEMBLER:
                next_stage = None
            if next_stage is not None:
                from ..agents.base_worker import make_task_message

                action = payload.get("action") or _default_action_for(next_stage)
                next_payload = dict(payload.get("next_payload") or {})
                # Always include the latest available translation so the
                # next stage doesn't need to re-fetch.
                if next_stage in (
                    "glossary_applier",
                    "consistency_checker",
                    "qa_validator",
                    "grammar_proofer",
                    "llm_polisher",
                ):
                    for key in (
                        "raw_translation",
                        "glossary_applied",
                        "qa_checked",
                        "grammar_checked",
                        "polished_translation",
                    ):
                        if key in payload and key not in next_payload:
                            next_payload[key] = payload[key]
                # Pre-fetch the current chunk from the StateStore so the
                # agent has access to source_text / chapter context.
                stored = self.store.get_chunk(chunk_id) or {}
                for key in (
                    "source_text",
                    "chapter_id",
                    "chapter_title",
                    "source_lang",
                    "target_lang",
                    "raw_translation",
                    "glossary_applied",
                    "qa_checked",
                    "grammar_checked",
                    "polished_translation",
                ):
                    if key in stored and key not in next_payload:
                        next_payload[key] = stored[key]
                # Pre-fetch the project context (langs).
                ctx = self._project
                if ctx is not None:
                    next_payload.setdefault("source_lang", ctx.source_lang)
                    next_payload.setdefault("target_lang", ctx.target_lang)
                # Pre-fetch the lexicon for the glossary stage.
                if next_stage == "glossary_applier":
                    next_payload["lexicon_terms"] = self.store.list_lexicon()
                # The QA / consistency / polisher stages may want the
                # current polished text passed through.
                if next_stage in (
                    "qa_validator",
                    "grammar_proofer",
                    "consistency_checker",
                ):
                    polished = stored.get("polished_translation")
                    if polished and "polished_translation" not in next_payload:
                        next_payload["polished_translation"] = polished
                # ConsistencyChecker benefits from a few neighbour
                # chunks from the same chapter — we look them up here
                # so the agent doesn't touch the StateStore.
                if next_stage == "consistency_checker":
                    chap = stored.get("chapter_id")
                    if chap:
                        neighbour_chunks = self.store.list_chunks(
                            chapter_id=chap, limit=20
                        )
                        next_payload["neighbours"] = [
                            {
                                "id": c.get("id"),
                                "source_text": c.get("source_text", ""),
                                "raw_translation": c.get("raw_translation"),
                                "glossary_applied": c.get("glossary_applied"),
                                "polished_translation": c.get("polished_translation"),
                            }
                            for c in neighbour_chunks
                            if c.get("id") != chunk_id
                        ]
                self._workers.queues_for(next_stage).input.put(
                    make_task_message(
                        chunk_id=chunk_id,
                        action=action,
                        payload=next_payload,
                    )
                )

        # 3. Emit a progress event.
        self._emit(
            {
                "type": "agent_done",
                "stage": stage,
                "chunk_id": chunk_id,
                "payload": payload,
            }
        )

        # 4. If a chunk just became 'polished' and all chunks are now
        #    polished, kick off the assembler.
        if payload.get("status") == "polished":
            try:
                self.maybe_auto_assemble()
            except Exception:
                logger.exception("auto-assemble dispatch failed")

    def _next_stage(self, stage: str) -> str | None:
        try:
            idx = DEFAULT_PIPELINE_ORDER.index(stage)
        except ValueError:
            return None
        if idx + 1 >= len(DEFAULT_PIPELINE_ORDER):
            return None
        return DEFAULT_PIPELINE_ORDER[idx + 1]

    def _on_worker_exit(self, slot, exit_code: int) -> None:
        logger.error(
            "Worker %s pid=%s exited unexpectedly (code=%s)",
            slot.stage,
            slot.process.pid,
            exit_code,
        )
        with self._lock:
            if self._project is not None:
                self._project.status = "error"
        self._emit(
            {
                "type": "worker_exit",
                "stage": slot.stage,
                "pid": slot.process.pid,
                "exit_code": exit_code,
            }
        )

    # ---------- assembler dispatch ----------

    def assemble_now(
        self,
        output_path: str | Path,
        fmt: str = "txt",
    ) -> dict[str, Any]:
        """Trigger the Assembler stage with the current set of chunks.

        Returns a summary dict. Errors are reported in the dict, not
        raised — the caller (FastAPI) is request-scoped.
        """
        if self._project is None:
            return {"status": "no_project", "chunk_count": 0}
        chunks = self.store.list_chunks()
        if not chunks:
            return {"status": "no_chunks", "chunk_count": 0}
        from ..agents.base_worker import make_task_message
        from ..formats import detect_format

        try:
            fmt = fmt or detect_format(self._project.source_path)
        except Exception:
            fmt = "txt"
        out = Path(output_path)
        if out.suffix == "":
            out = out.with_suffix(f".{fmt}")
        try:
            queues = self._workers.queues_for("assembler")
        except KeyError:
            return {"status": "assembler_unavailable", "chunk_count": 0}
        queues.input.put(
            make_task_message(
                chunk_id=self._project.project_id,
                action="assemble",
                payload={
                    "chunks": chunks,
                    "output_path": str(out),
                    "format": fmt,
                    "title": self._project.project_id,
                    "manifest_path": self.store.get_state("project_manifest_path"),
                },
            )
        )
        self._emit(
            {
                "type": "assemble_triggered",
                "output_path": str(out),
                "format": fmt,
                "chunk_count": len(chunks),
            }
        )
        return {
            "status": "dispatched",
            "output_path": str(out),
            "format": fmt,
            "chunk_count": len(chunks),
        }

    def maybe_auto_assemble(self) -> None:
        """If all chunks are polished, kick off the assembler.

        The output path is `<project_dir>/target/<source_stem>.<fmt>`.
        """
        with self._lock:
            proj = self._project
        if proj is None or proj.status == "stopped":
            return
        total = self.store.count_chunks()
        if total == 0:
            return
        polished = self.store.count_chunks(status="polished")
        if polished < total:
            return
        out_dir = Path(proj.project_dir) / "target"
        out_dir.mkdir(parents=True, exist_ok=True)
        from ..formats import detect_format

        try:
            fmt = detect_format(proj.source_path)
        except Exception:
            fmt = "txt"
        out = out_dir / f"{Path(proj.source_path).stem}.{fmt}"
        self.assemble_now(out, fmt=fmt)


def _default_action_for(stage: str) -> str:
    return {
        "parser": "parse",
        "fast_translator": "translate",
        "lexicon_builder": "build_lexicon",
        "glossary_applier": "apply_glossary",
        "consistency_checker": "check_consistency",
        "qa_validator": "qa_check",
        "grammar_proofer": "proofread",
        "llm_polisher": "polish",
        "assembler": "assemble",
    }.get(stage, "process")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


__all__ = ["Orchestrator", "ProjectContext"]
