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

import hashlib
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
    PARSER,
    STAGE_TO_STATUS,
    STATUS_ERROR,
    StageSpec,
    build_stages,
    get_profile_order,
)
from .state_store import StateStore
from .worker_manager import WorkerManager

logger = logging.getLogger(__name__)


# Callback signature for state changes (used by the WebSocket layer).
StateListener = Callable[[dict[str, Any]], None]


# Drain loop: when a single stage output queue is saturated, we drain
# up to this many of its messages per loop iteration before moving on.
# Keeps a chatty stage from starving quieter ones.
MAX_DRAIN_PER_STAGE_PER_LOOP = 8


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
    profile: str = "balanced"
    output_format: str = "txt"


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

    @property
    def _stage_order(self) -> tuple[str, ...]:
        """Stage order for the current project's profile."""
        if self._project is not None:
            return get_profile_order(self._project.profile)
        return DEFAULT_PIPELINE_ORDER

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
                    "profile": project.profile,
                },
            )
        # Reset LLM usage counters for the new run.
        try:
            from ..llm_router.router import get_router
            get_router().reset_usage()
        except Exception:
            pass

        for stage in self._stage_order:
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
            for stage in self._stage_order:
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
            for stage in self._stage_order:
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
        spec = self._stages["fast_translator"]
        q = self._workers.queues_for(spec.key).input
        count = 0
        for chunk in chunks:
            chunk_id = chunk.get("id") or uuid.uuid4().hex
            chunk.setdefault("id", chunk_id)
            source_text = chunk.get("source_text") or ""
            source_hash = chunk.get("source_hash")
            # Compute and store the hash if not already present.
            if not source_hash:
                source_hash = self._compute_source_hash(source_text)
                chunk["source_hash"] = source_hash
            self.store.add_chunk(chunk)
            self.store.update_chunk_field(chunk_id, "status", "parsed")
            from ..agents.base_worker import make_task_message

            # Verify the source hash before queuing.
            if not self._verify_chunk_hash(chunk_id, source_text, source_hash):
                continue

            # The orchestrator is the single reader of the StateStore;
            # we pre-fetch the source text so the agent never has to.
            stored = self.store.get_chunk(chunk_id) or {}
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

    # ---------- chunk hash verification ----------

    @staticmethod
    def _compute_source_hash(source_text: str) -> str:
        return hashlib.sha256(source_text.encode("utf-8")).hexdigest()

    def _verify_chunk_hash(
        self, chunk_id: str, source_text: str, expected_hash: str | None
    ) -> bool:
        if not expected_hash:
            return True
        actual = self._compute_source_hash(source_text)
        if actual != expected_hash:
            logger.error(
                "Hash mismatch for chunk %s: expected %s, got %s",
                chunk_id, expected_hash, actual,
            )
            self.store.update_chunk_field(chunk_id, "status", STATUS_ERROR)
            self.store.update_chunk_field(
                chunk_id, "error_message",
                f"hash_mismatch: expected={expected_hash} actual={actual}",
            )
            self._emit(
                {
                    "type": "chunk_hash_mismatch",
                    "chunk_id": chunk_id,
                    "expected": expected_hash,
                    "actual": actual,
                }
            )
            return False
        return True

    def replay_chunks(self, chunk_ids: list[str]) -> int:
        """Re-inject errored chunks into the pipeline.

        Resets each chunk's status and clears the error message. If a
        chunk already has a ``raw_translation`` (i.e. it errored after
        the FastTranslator stage), it skips re-translation and is
        re-queued at ``fast_translated`` status so the remaining
        downstream stages can re-process it.
        """
        from ..agents.base_worker import make_task_message

        try:
            queues = self._workers.queues_for("fast_translator")
        except KeyError:
            logger.warning("replay_chunks: translator not running")
            return 0
        count = 0
        for chunk_id in chunk_ids:
            stored = self.store.get_chunk(chunk_id)
            if stored is None:
                continue
            raw = stored.get("raw_translation")
            source_text = stored.get("source_text") or ""
            source_hash = self._compute_source_hash(source_text)
            self.store.update_chunk_field(chunk_id, "source_hash", source_hash)
            self.store.update_chunk_field(chunk_id, "error_message", None)
            if raw:
                self.store.update_chunk_field(chunk_id, "status", "fast_translated")
                self.store.update_chunk_field(chunk_id, "raw_translation", raw)
                self._on_stage_done("fast_translator", chunk_id, {
                    "status": "fast_translated",
                    "raw_translation": raw,
                })
            else:
                self.store.update_chunk_field(chunk_id, "status", "parsed")
                queues.input.put(
                    make_task_message(
                        chunk_id=chunk_id,
                        action="translate",
                        payload={
                            "source_text": source_text,
                            "chapter_id": stored.get("chapter_id"),
                            "chapter_title": stored.get("chapter_title"),
                            "neighbor_chars": 300,
                        },
                    )
                )
            count += 1
        if count:
            self._emit(
                {
                    "type": "chunks_replayed",
                    "count": count,
                    "chunk_ids": chunk_ids,
                    "timestamp": _now_iso(),
                }
            )
        return count

    # ---------- HITL ----------

    def register_hltl(self, msg: dict[str, Any]) -> None:
        """Record a human-in-the-loop request emitted by an agent.

        The record is held both in memory (for the snapshot / GUI polling)
        and persisted in `pending_hltl` (for crash-safe replay).
        """
        chunk_id = msg.get("chunk_id")
        if not chunk_id:
            return
        issue = (msg.get("payload") or {}).get("issue", {})
        request_id = uuid.uuid4().hex
        received_at = _now_iso()
        record = {
            "request_id": request_id,
            "chunk_id": chunk_id,
            "stage": msg.get("stage"),
            "issue": issue,
            "received_at": received_at,
        }
        with self._lock:
            self._pending_hltl[request_id] = record
            self.store.update_chunk_field(chunk_id, "status", "waiting_for_human")
        try:
            self.store.register_hltl_record(
                request_id=request_id,
                chunk_id=chunk_id,
                stage=msg.get("stage") or "",
                issue=issue,
                received_at=received_at,
            )
        except Exception:
            logger.exception("hltl: failed to persist pending_hltl record")
        self._emit(
            {
                "type": "hltl_alert",
                "request_id": request_id,
                "chunk_id": chunk_id,
                "stage": msg.get("stage"),
                "issue": issue,
                "timestamp": received_at,
            }
        )

    def respond_hltl(self, request_id: str, answer: str) -> bool:
        """Apply a human answer to a pending HITL request.

        If the target stage has no live worker (or the stage is unknown),
        the chunk stays in `waiting_for_human`, an `hltl_unroutable`
        event is emitted, and the `pending_hltl` record is left
        unresolved so a later `replay_pending_hltl` can pick it up.
        Only on a successful re-injection do we mark the record resolved.
        """
        with self._lock:
            record = self._pending_hltl.pop(request_id, None)
        if record is None:
            return False
        chunk_id = record["chunk_id"]
        target_stage = record.get("stage")
        resolved_at = _now_iso()
        # Always record the human answer for audit.
        self.store.set_state(
            f"hltl_response:{request_id}",
            {
                "answer": answer,
                "chunk_id": chunk_id,
                "responded_at": resolved_at,
            },
        )
        if not target_stage or target_stage not in self._stages:
            self._emit(
                {
                    "type": "hltl_unroutable",
                    "request_id": request_id,
                    "chunk_id": chunk_id,
                    "stage": target_stage,
                    "reason": "unknown_stage",
                    "timestamp": resolved_at,
                }
            )
            return True
        if not self._workers.is_alive(target_stage):
            logger.info(
                "hltl: target stage %s has no live worker; chunk %s "
                "remains waiting_for_human",
                target_stage,
                chunk_id,
            )
            self._emit(
                {
                    "type": "hltl_unroutable",
                    "request_id": request_id,
                    "chunk_id": chunk_id,
                    "stage": target_stage,
                    "reason": "worker_dead",
                    "timestamp": resolved_at,
                }
            )
            # Keep the request_id in the in-memory map so a follow-up
            # replay can still act on it without round-tripping to disk.
            with self._lock:
                self._pending_hltl[request_id] = record
            return True
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
        try:
            self.store.resolve_hltl_record(request_id, resolved_at)
        except Exception:
            logger.exception("hltl: failed to mark record resolved")
        logger.info(
            "hltl: chunk %s waiting_for_human -> parsed (re-injected to %s)",
            chunk_id,
            target_stage,
        )
        self._emit(
            {
                "type": "hltl_resolved",
                "request_id": request_id,
                "chunk_id": chunk_id,
                "answer": answer,
                "timestamp": resolved_at,
            }
        )
        return True

    def replay_pending_hltl(self) -> dict[str, int]:
        """Re-route any HITL requests that were left unrouted.

        Intended to be called after a worker restart. Returns a summary
        of how many requests were re-injected vs left pending.
        """
        routed = 0
        skipped = 0
        # Reload from store in case we restarted without an in-memory copy.
        for rec in self.store.list_unresolved_hltl():
            request_id = rec["request_id"]
            with self._lock:
                if request_id in self._pending_hltl:
                    skipped += 1
                    continue
                self._pending_hltl[request_id] = rec
            self.store.update_chunk_field(
                rec["chunk_id"], "status", "waiting_for_human"
            )
            self._emit(
                {
                    "type": "hltl_replay_started",
                    "request_id": request_id,
                    "chunk_id": rec["chunk_id"],
                    "stage": rec["stage"],
                }
            )
            target_stage = rec.get("stage")
            if not target_stage or target_stage not in self._stages:
                skipped += 1
                continue
            if not self._workers.is_alive(target_stage):
                self._emit(
                    {
                        "type": "hltl_unroutable",
                        "request_id": request_id,
                        "chunk_id": rec["chunk_id"],
                        "stage": target_stage,
                        "reason": "worker_still_dead",
                    }
                )
                skipped += 1
                continue
            q = self._workers.queues_for(target_stage).input
            from ..agents.base_worker import make_task_message

            q.put(
                make_task_message(
                    chunk_id=rec["chunk_id"],
                    action="hltl_reprocess",
                    payload={"answer": None, "issue": rec.get("issue")},
                )
            )
            self.store.update_chunk_field(
                rec["chunk_id"], "status", "parsed"
            )
            self._emit(
                {
                    "type": "hltl_resolved",
                    "request_id": request_id,
                    "chunk_id": rec["chunk_id"],
                    "answer": None,
                    "note": "replayed",
                }
            )
            routed += 1
        return {"routed": routed, "skipped": skipped}

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

    # ---------- internals: run-level and drain loop ----------

    def _handle_run_level_message(
        self, stage: str, payload: dict[str, Any]
    ) -> None:
        """Process a project-level (chunk_id=None) completion message.

        Currently only the Parser uses this path: it produces a manifest
        and a list of chapters/chunks that must be injected into the
        FastTranslator queue (the regular forward path can't do it
        because the Parser's `terminal=True` flag would block it).
        """
        if stage == PARSER:
            if payload.get("manifest_path"):
                self.store.set_state(
                    "project_manifest_path", payload["manifest_path"]
                )
            if payload.get("target_path"):
                self.store.set_state("target_path", payload["target_path"])
            chapters = payload.get("chapters") or []
            source_file = str(payload.get("source_path") or "")
            flat: list[dict[str, Any]] = []
            for chap in chapters:
                for c in chap.get("chunks") or []:
                    c.setdefault("chapter_id", chap.get("id"))
                    c.setdefault("chapter_title", chap.get("title"))
                    if source_file and "source_file" not in c:
                        c["source_file"] = source_file
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
        # Unknown stage at run level: log and let listeners see it.
        logger.warning("run-level completion from unknown stage %r", stage)
        self._emit(
            {
                "type": "agent_done",
                "stage": stage,
                "chunk_id": None,
                "payload": payload,
            }
        )

    def _drain_loop(self) -> None:
        """Read every stage's output queue, update the store, forward chunks.

        Round-robin across stages with a soft back-pressure: when a queue
        is saturated (size >= MAX_DRAIN_PER_STAGE_PER_LOOP), drain up to
        that cap from it before moving on, so a chatty stage cannot
        starve quieter ones.

        Iterates only the stages active in the current project profile.
        """
        while not self._stop_drain.is_set():
            stage_order = self._stage_order
            did_work = False
            for stage in stage_order:
                if stage not in self._stages:
                    continue
                try:
                    q = self._workers.queues_for(stage).output
                except KeyError:
                    continue
                try:
                    pending = q.qsize()
                except Exception:
                    pending = 0
                cap = MAX_DRAIN_PER_STAGE_PER_LOOP if pending >= MAX_DRAIN_PER_STAGE_PER_LOOP else 1
                for _ in range(cap):
                    try:
                        msg = q.get_nowait()
                    except Exception:
                        break
                    did_work = True
                    self._handle_worker_message(stage, msg)
            if not did_work:
                time.sleep(0.05)

    _WORKER_MSG_DISPATCH = {
        "error": "_handle_worker_error",
        "hltl_request": "_handle_worker_hltl_request",
        "progress": "_handle_worker_progress",
        "run_done": "_handle_worker_run_done",
        "done": "_handle_worker_done",
    }

    def _handle_worker_message(self, stage: str, msg: dict[str, Any]) -> None:
        msg_type = msg.get("type")
        handler_name = self._WORKER_MSG_DISPATCH.get(msg_type)
        if handler_name is None:
            logger.debug("Unhandled message from %s: %r", stage, msg)
            return
        getattr(self, handler_name)(stage, msg)

    def _handle_worker_error(self, stage: str, msg: dict[str, Any]) -> None:
        chunk_id = msg.get("chunk_id")
        payload = msg.get("payload") or {}
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

    def _handle_worker_hltl_request(self, stage: str, msg: dict[str, Any]) -> None:
        self.register_hltl(msg)

    def _handle_worker_progress(self, stage: str, msg: dict[str, Any]) -> None:
        chunk_id = msg.get("chunk_id")
        payload = msg.get("payload") or {}
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

    def _handle_worker_run_done(self, stage: str, msg: dict[str, Any]) -> None:
        payload = msg.get("payload") or {}
        self._handle_run_level_message(stage, payload)

    def _handle_worker_done(self, stage: str, msg: dict[str, Any]) -> None:
        chunk_id = msg.get("chunk_id")
        payload = msg.get("payload") or {}
        # run_done is a project-level completion (chunk_id=None). Any
        # stage may emit it when it finishes its run-level work; we
        # delegate to a dedicated handler.
        if chunk_id is None:
            self._handle_run_level_message(stage, payload)
            return
        self._persist_done_side_effects(stage, chunk_id, payload)
        self._on_stage_done(stage, chunk_id, payload)

    def _persist_done_side_effects(
        self, stage: str, chunk_id: str, payload: dict[str, Any]
    ) -> None:
        if stage == "lexicon_builder" and payload.get("terms"):
            self._persist_lexicon_terms(payload.get("terms") or [])
        if stage == "grammar_proofer" and payload.get("grammar_issues"):
            self._persist_grammar_issues(chunk_id, payload.get("grammar_issues") or [])
        if stage == "qa_validator" and payload.get("qa_issues"):
            self._persist_qa_issues(chunk_id, payload.get("qa_issues") or [])
        if stage == "consistency_checker" and payload.get("consistency_flags"):
            self._persist_consistency_flags(
                chunk_id, payload.get("consistency_flags") or []
            )

    def _persist_lexicon_terms(self, terms: list[Any]) -> None:
        for term in terms:
            if isinstance(term, dict) and "id" in term:
                try:
                    self.store.add_lexicon_term(term)
                except Exception:
                    logger.exception("lexicon: failed to persist term")

    def _persist_grammar_issues(self, chunk_id: str, issues: list[Any]) -> None:
        import uuid as _uuid

        for issue in issues:
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

    def _persist_qa_issues(self, chunk_id: str, issues: list[Any]) -> None:
        import uuid as _uuid

        for issue in issues:
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

    def _persist_consistency_flags(self, chunk_id: str, flags: list[Any]) -> None:
        import uuid as _uuid

        for flag in flags:
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

    def _on_stage_done(
        self, stage: str, chunk_id: str | None, payload: dict[str, Any]
    ) -> None:
        if not chunk_id:
            return
        self._emit_artifact_if_assembler(stage, chunk_id, payload)
        self._persist_chunk_fields(chunk_id, payload)
        self._emit_agent_done(stage, chunk_id, payload)
        self._maybe_auto_assemble(payload)
        if payload.get("terminal"):
            return
        next_stage = self._next_stage(stage)
        if next_stage is None or next_stage == ASSEMBLER:
            return
        next_stage = self._maybe_escalate(stage, next_stage, chunk_id, payload)
        if not self._maybe_reflect(stage, chunk_id, payload):
            return
        self._forward_to_next_stage(next_stage, chunk_id, payload)

    # ----- _on_stage_done sub-steps -----

    def _emit_artifact_if_assembler(
        self, stage: str, chunk_id: str, payload: dict[str, Any]
    ) -> None:
        if stage != ASSEMBLER:
            return
        if not payload.get("output_path"):
            return
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

    def _persist_chunk_fields(self, chunk_id: str, payload: dict[str, Any]) -> None:
        for field_name in (
            "raw_translation",
            "glossary_applied",
            "qa_checked",
            "grammar_checked",
            "polished_translation",
        ):
            if field_name in payload:
                self.store.update_chunk_field(
                    chunk_id, field_name, payload[field_name]
                )
        if "review_score" in payload:
            self.store.update_chunk_field(
                chunk_id, "review_score", payload["review_score"]
            )
        if "review_annotations" in payload:
            import json as _json

            self.store.update_chunk_field(
                chunk_id,
                "review_annotations",
                _json.dumps(payload["review_annotations"], ensure_ascii=False),
            )
        new_status = payload.get("status") or STAGE_TO_STATUS.get(stage, "parsed")
        self.store.update_chunk_field(chunk_id, "status", new_status)

    def _maybe_escalate(
        self,
        stage: str,
        next_stage: str | None,
        chunk_id: str,
        payload: dict[str, Any],
    ) -> str | None:
        """Apply DAG shortcuts and escalation policies.

        Current policies:
          * qa_clean + balanced/premium → skip grammar_proofer to reviewer.
          * consistency flag on premium profile → branch to terminology_researcher.
          * qa_issues on any profile → keep grammar_proofer (do not skip).
        """
        if next_stage is None:
            return None
        order = self._stage_order
        profile = self._project.profile if self._project else "balanced"

        # Policy A: clean QA can bypass grammar_proofer in balanced/premium.
        if stage == "qa_validator" and next_stage == "grammar_proofer":
            if profile in ("balanced", "premium") and not payload.get("qa_issues"):
                if "reviewer" in order:
                    self._emit(
                        {
                            "type": "dag_skip",
                            "chunk_id": chunk_id,
                            "skipped": "grammar_proofer",
                            "reason": "qa_clean",
                        }
                    )
                    return "reviewer"

        # Policy B: consistency flags in premium trigger terminology research.
        if (
            stage == "consistency_checker"
            and profile == "premium"
            and "terminology_researcher" in order
        ):
            flags = payload.get("consistency_flags") or []
            if flags:
                self._emit(
                    {
                        "type": "dag_escalate",
                        "chunk_id": chunk_id,
                        "from": "consistency_checker",
                        "to": "terminology_researcher",
                        "reason": "consistency_flag",
                    }
                )
                return "terminology_researcher"

        return next_stage

    # Profile-specific reflection thresholds. Eco has no reviewer at all.
    REFLEXION_THRESHOLD: dict[str, float] = {
        "eco": 0.0,  # reviewer not used
        "balanced": 0.7,
        "premium": 0.85,
    }

    def _reflection_threshold(self) -> float:
        """Return the review-score threshold below which a reflection is triggered."""
        profile = self._project.profile if self._project else "balanced"
        return self.REFLEXION_THRESHOLD.get(profile, 0.7)

    def _maybe_reflect(
        self, stage: str, chunk_id: str, payload: dict[str, Any]
    ) -> bool:
        """Re-inject the chunk into llm_polisher if the reviewer scored low.

        Returns False if the chunk was reflected (caller must stop
        forwarding); True otherwise. If the maximum number of reflection
        loops is exhausted, the chunk is escalated to HITL.
        """
        if stage != "reviewer":
            return True
        score = payload.get("review_score", 1.0)
        threshold = self._reflection_threshold()
        if score >= threshold:
            return True
        stored_chunk = self.store.get_chunk(chunk_id) or {}
        stored_meta = dict(stored_chunk.get("metadata") or {})
        reflection_count = int(stored_meta.get("reflection_count") or 0)
        max_reflections = 2
        if reflection_count >= max_reflections:
            self._emit(
                {
                    "type": "reflection_exhausted",
                    "chunk_id": chunk_id,
                    "score": score,
                    "reflection_count": reflection_count,
                }
            )
            self.register_hltl(
                {
                    "type": "hltl_request",
                    "stage": "reviewer",
                    "chunk_id": chunk_id,
                    "payload": {
                        "issue": {
                            "summary": f"Review score {score:.2f} below threshold {threshold:.2f} after {reflection_count} reflection(s)",
                            "kind": "reflection_exhausted",
                        }
                    },
                }
            )
            return True
        reflection_count += 1
        stored_meta["reflection_count"] = reflection_count
        import json as _json

        self.store.update_chunk_field(
            chunk_id,
            "metadata_json",
            _json.dumps(stored_meta, ensure_ascii=False),
        )
        self._enqueue_reflection(chunk_id, payload, stored_chunk, score, reflection_count)
        return False

    def _enqueue_reflection(
        self,
        chunk_id: str,
        payload: dict[str, Any],
        stored_chunk: dict[str, Any],
        score: float,
        reflection_count: int,
    ) -> None:
        from ..agents.base_worker import make_task_message

        annotations = payload.get("review_annotations") or []
        annot_text = (
            "; ".join(
                f"[{a.get('type', '')}] {a.get('span', '')} → {a.get('suggestion', '')}"
                for a in annotations[:5]
            )
            if annotations
            else ""
        )
        src_for_reflect = payload.get("source_text") or stored_chunk.get("source_text") or ""
        tgt_for_reflect = (
            payload.get("polished_translation")
            or payload.get("grammar_checked")
            or stored_chunk.get("polished_translation")
            or stored_chunk.get("grammar_checked")
            or stored_chunk.get("glossary_applied")
            or stored_chunk.get("raw_translation")
            or ""
        )
        reflection_payload = {
            "source_text": src_for_reflect,
            "polished_translation": tgt_for_reflect,
            "review_score": score,
            "review_annotations": annotations,
            "reflection_instructions": (
                f"Reviewer score: {score:.2f}. Issues: {annot_text}. "
                "Please revise the translation accordingly."
            )
            if annot_text
            else f"Reviewer score: {score:.2f}. Please improve.",
            "reflection_count": reflection_count,
        }
        self._workers.queues_for("llm_polisher").input.put(
            make_task_message(
                chunk_id=chunk_id,
                action="polish",
                payload=reflection_payload,
            )
        )
        self._emit(
            {
                "type": "reflection_triggered",
                "chunk_id": chunk_id,
                "score": score,
                "reflection_count": reflection_count,
            }
        )

    def _forward_to_next_stage(
        self, next_stage: str, chunk_id: str, payload: dict[str, Any]
    ) -> None:
        from ..agents.base_worker import make_task_message

        action = payload.get("action") or _default_action_for(next_stage)
        next_payload = dict(payload.get("next_payload") or {})

        self._propagate_translation_fields(next_stage, payload, next_payload)

        # Verify source hash integrity before forwarding.
        stored = self.store.get_chunk(chunk_id) or {}
        src_text = stored.get("source_text") or ""
        src_hash = stored.get("source_hash")
        if not self._verify_chunk_hash(chunk_id, src_text, src_hash):
            return

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
            "review_score",
            "review_annotations",
        ):
            if key in stored and key not in next_payload:
                next_payload[key] = stored[key]

        ctx = self._project
        if ctx is not None:
            next_payload.setdefault("source_lang", ctx.source_lang)
            next_payload.setdefault("target_lang", ctx.target_lang)

        if next_stage == "glossary_applier":
            next_payload["lexicon_terms"] = self.store.list_lexicon()

        if next_stage in (
            "qa_validator",
            "grammar_proofer",
            "consistency_checker",
        ):
            polished = stored.get("polished_translation")
            if polished and "polished_translation" not in next_payload:
                next_payload["polished_translation"] = polished

        if next_stage == "consistency_checker":
            self._attach_neighbour_chunks(stored, chunk_id, next_payload)

        self._workers.queues_for(next_stage).input.put(
            make_task_message(
                chunk_id=chunk_id,
                action=action,
                payload=next_payload,
            )
        )

    def _propagate_translation_fields(
        self,
        next_stage: str,
        payload: dict[str, Any],
        next_payload: dict[str, Any],
    ) -> None:
        if next_stage not in (
            "glossary_applier",
            "consistency_checker",
            "qa_validator",
            "grammar_proofer",
            "reviewer",
            "llm_polisher",
        ):
            return
        for key in (
            "raw_translation",
            "glossary_applied",
            "qa_checked",
            "grammar_checked",
            "polished_translation",
            "review_score",
            "review_annotations",
        ):
            if key in payload and key not in next_payload:
                next_payload[key] = payload[key]

    def _attach_neighbour_chunks(
        self,
        stored: dict[str, Any],
        chunk_id: str,
        next_payload: dict[str, Any],
    ) -> None:
        chap = stored.get("chapter_id")
        if not chap:
            return
        neighbour_chunks = self.store.list_chunks(chapter_id=chap, limit=20)
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

    def _emit_agent_done(
        self, stage: str, chunk_id: str, payload: dict[str, Any]
    ) -> None:
        self._emit(
            {
                "type": "agent_done",
                "stage": stage,
                "chunk_id": chunk_id,
                "payload": payload,
            }
        )

    def _maybe_auto_assemble(self, payload: dict[str, Any]) -> None:
        threshold_status = self._penultimate_status()
        if not threshold_status or payload.get("status") != threshold_status:
            return
        try:
            self.maybe_auto_assemble()
        except Exception:
            logger.exception("auto-assemble dispatch failed")

    def _next_stage(self, stage: str) -> str | None:
        order = self._stage_order
        try:
            idx = order.index(stage)
        except ValueError:
            return None
        if idx + 1 >= len(order):
            return None
        return order[idx + 1]

    def _penultimate_status(self) -> str | None:
        """Return the chunk status produced by the stage just before
        the assembler in the current profile. Used by auto-assemble."""
        order = self._stage_order
        if ASSEMBLER not in order or len(order) < 2:
            return None
        idx = order.index(ASSEMBLER)
        if idx == 0:
            return None
        penultimate = order[idx - 1]
        return STAGE_TO_STATUS.get(penultimate)

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
        """If all chunks have reached the penultimate stage in the current
        profile, kick off the assembler.

        The output path is ``<project_dir>/target/<source_stem>.<fmt>``.
        """
        threshold = self._penultimate_status()
        if threshold is None:
            return
        with self._lock:
            proj = self._project
        if proj is None or proj.status == "stopped":
            return
        total = self.store.count_chunks()
        if total == 0:
            return
        ready = self.store.count_chunks(status=threshold)
        if ready < total:
            return
        out_dir = Path(proj.project_dir) / "target"
        out_dir.mkdir(parents=True, exist_ok=True)
        fmt = proj.output_format or "txt"
        out = out_dir / f"{Path(proj.source_path).stem}.{fmt}"
        self.assemble_now(out, fmt=fmt)


def _default_action_for(stage: str) -> str:
    return {
        "parser": "parse",
        "fast_translator": "translate",
        "lexicon_builder": "build_lexicon",
        "terminology_researcher": "research_terms",
        "glossary_applier": "apply_glossary",
        "consistency_checker": "check_consistency",
        "qa_validator": "qa_check",
        "grammar_proofer": "proofread",
        "reviewer": "review",
        "llm_polisher": "polish",
        "assembler": "assemble",
    }.get(stage, "process")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


__all__ = ["Orchestrator", "ProjectContext"]
