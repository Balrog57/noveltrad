"""Central orchestrator -- coordination of pipeline stages.

Responsibilities (see plan section1, section3, section5):
  * Own the StateStore (single writer).
  * Own the WorkerManager (lifecycle of agent processes).
  * Drain every stage's output queue, update the StateStore, and forward
    the chunk to the next stage's input queue.
  * Maintain in-memory `project_state` and `pipeline_state` for the
    FastAPI layer to query (cheap, no need to hit the DB on every GUI poll).
  * Surface progress / errors / HITL requests to subscribers -- in
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

Module layout
-------------
After the v4 split, this module holds only the lifecycle, the drain
loop, the listener fanout, the snapshot, the assembler dispatch, and
the HITL handlers. The internal "what to do when a worker reports
done" logic lives in :mod:`.collaborators` as four small classes:

  * ``persister``  -- the persist_* family and the forward-to-next-stage logic.
  * ``dispatcher`` -- the _handle_worker_* message dispatch.
  * ``queue``      -- the sequential project queue.
  * ``reflection`` -- the reflection / escalation DAG.

The orchestrator owns one of each and exposes thin delegates for the
private API the test suite uses (``_on_stage_done``,
``_reflection_threshold``).
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

from .collaborators import (
    ChunkPersister,
    MessageDispatcher,
    ProjectQueue,
    ReflectionController,
    Watchdog,
)
from .pipeline import (
    ASSEMBLER,
    DEFAULT_PIPELINE_ORDER,
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


# Pipeline-stage constants. Re-exported as instance attributes in
# ``Orchestrator.__init__`` so the collaborators can read them as
# ``self._orch.ASSEMBLER`` etc.
PARSER = PARSER
ASSEMBLER = ASSEMBLER
STAGE_TO_STATUS = STAGE_TO_STATUS
STATUS_ERROR = STATUS_ERROR


@dataclass
class ProjectContext:
    """All per-project state held in memory by the orchestrator."""

    project_id: str
    project_dir: Path
    source_lang: str
    target_lang: str
    # ``source_path`` is the first source file (back-compat); the full
    # list lives in ``source_paths`` and is what the Parser and
    # Assembler actually iterate on.
    source_path: Path | None = None
    source_paths: list[Path] = field(default_factory=list)
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
        # Watchdog: tracks when the last chunk event was emitted so
        # we can surface a warning when a project has been running for
        # a long time without any progress (worker stuck / crashed).
        self._last_progress_at: float = time.time()
        self._last_stall_warn_at: float = 0.0

        # Collaborators: each one owns a focused responsibility and
        # reads shared state through this orchestrator.
        self.persister = ChunkPersister(self)
        self.dispatcher = MessageDispatcher(self)
        self.queue: ProjectQueue = ProjectQueue(self)
        self.reflection = ReflectionController(self)
        self.watchdog = Watchdog(self)

        self._drain_thread: threading.Thread | None = None
        self._stop_drain = threading.Event()
        self._listeners: list[StateListener] = []
        self._event_log: deque[dict[str, Any]] = deque(maxlen=500)
        self._pending_hltl: dict[str, dict[str, Any]] = {}
        self._paused_stages: set[str] = set()

    # ------------------------------------------------------------------
    # Stage constants used by collaborators
    # ------------------------------------------------------------------

    PARSER = PARSER
    ASSEMBLER = ASSEMBLER
    STAGE_TO_STATUS = STAGE_TO_STATUS
    STATUS_ERROR = STATUS_ERROR

    # ------------------------------------------------------------------
    # Helpers exposed to collaborators
    # ------------------------------------------------------------------

    @staticmethod
    def _default_action_for(stage: str) -> str:
        return {
            "parser": "parse",
            "fast_translator": "translate",
            "lexicon_builder": "build_lexicon",
            "terminology_researcher": "research_terms",
            "glossary_applier": "apply_glossary",
            "llm_refiner": "refine",
            "consistency_checker": "check_consistency",
            "qa_validator": "qa_check",
            "grammar_proofer": "proofread",
            "reviewer": "review",
            "llm_polisher": "polish",
            "assembler": "assemble",
        }.get(stage, "process")

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

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

    # ------------------------------------------------------------------
    # project lifecycle
    # ------------------------------------------------------------------

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
                # Pipeline busy: enqueue and return immediately.
                self.queue.append(project)
                return
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

        # Build the parser message. We include both ``source_path``
        # (legacy single-file workers) and ``source_paths`` (the
        # multi-file flow added in v4.1.9).
        source_paths_payload = (
            [str(p) for p in project.source_paths]
            if project.source_paths
            else ([str(project.source_path)] if project.source_path else [])
        )
        parser_payload = {
            "project_id": project.project_id,
            "project_dir": str(project.project_dir),
            "source_paths": source_paths_payload,
            "source_path": (
                source_paths_payload[0] if len(source_paths_payload) == 1 else None
            ),
            "source_lang": project.source_lang,
            "target_lang": project.target_lang,
            "output_path": str(project.output_path) if project.output_path else None,
        }
        try:
            self._workers.queues_for("parser").input.put(
                make_task_message(
                    chunk_id=project.project_id,
                    action="parse",
                    payload=parser_payload,
                ),
                timeout=5.0,
            )
        except Exception:
            # If we cannot even reach the parser queue (no worker
            # alive, queue closed, ...), surface the failure and
            # keep the rest of the queue moving.
            logger.exception(
                "orchestrator: failed to dispatch parser task for %s",
                project.project_id,
            )
            self._emit({
                "type": "agent_error",
                "stage": PARSER,
                "chunk_id": None,
                "payload": {
                    "error_kind": "parser_dispatch_failed",
                    "message": "failed to dispatch parser task",
                },
            })
            with self._lock:
                if self._project is not None:
                    self._project.status = "error"
            self.queue.start_next()
            return
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
            # Drop any pending queue entries on explicit stop so
            # a stopped orchestrator does not silently start them
            # when the user hits Start again.
            self.queue.clear()
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

    # ------------------------------------------------------------------
    # chunk submission
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # chunk hash verification
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # HITL
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # listeners (WebSocket fanout stub)
    # ------------------------------------------------------------------

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
        # Update the watchdog: any event means the pipeline is alive.
        self._last_progress_at = time.time()
        with self._lock:
            self._event_log.append(event)
            listeners = list(self._listeners)
        for cb in listeners:
            try:
                cb(event)
            except Exception:
                logger.exception("Listener raised; dropping event %s", event.get("type"))

    # ------------------------------------------------------------------
    # query
    # ------------------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            project = self._project
            queue = [
                {
                    "project_id": q.project_id,
                    "source_path": str(q.source_path) if q.source_path else None,
                    "source_paths": [str(p) for p in q.source_paths],
                    "profile": q.profile,
                }
                for q in self.queue
            ]
        return {
            "project": (
                {
                    "project_id": project.project_id,
                    "status": project.status,
                    "source_lang": project.source_lang,
                    "target_lang": project.target_lang,
                    "started_at": project.started_at,
                    "source_path": str(project.source_path)
                    if project.source_path
                    else None,
                    "source_paths": [str(p) for p in project.source_paths],
                    "profile": project.profile,
                    "output_format": project.output_format,
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
            "project_queue": queue,
            "project_queue_size": len(queue),
        }

    def recent_events(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._event_log)[-limit:]

    # ------------------------------------------------------------------
    # backward-compatible thin delegates (tests + callers rely on these
    # private hooks; the orchestrator keeps them as one-liners that call
    # into the matching collaborator).
    # ------------------------------------------------------------------

    @property
    def _project_queue(self) -> list:
        """Back-compat alias for ``self.queue``.

        Older callers and the v4.1.10 test suite inspect the queue as
        ``orch._project_queue``. After the v4 split the real list lives
        inside ``ProjectQueue._items``; this property re-exposes it so
        existing tests do not need to change.
        """
        return self.queue._items

    def _on_stage_done(
        self, stage: str, chunk_id: str | None, payload: dict[str, Any]
    ) -> None:
        self.persister.on_stage_done(stage, chunk_id, payload)

    def _handle_worker_message(self, stage: str, msg: dict[str, Any]) -> None:
        self.dispatcher.handle(stage, msg)

    def _handle_worker_error(self, stage: str, msg: dict[str, Any]) -> None:
        self.dispatcher.handle_worker_error(stage, msg)

    def _handle_worker_hltl_request(self, stage: str, msg: dict[str, Any]) -> None:
        self.dispatcher.handle_worker_hltl_request(stage, msg)

    def _handle_worker_progress(self, stage: str, msg: dict[str, Any]) -> None:
        self.dispatcher.handle_worker_progress(stage, msg)

    def _handle_worker_run_done(self, stage: str, msg: dict[str, Any]) -> None:
        self.dispatcher.handle_worker_run_done(stage, msg)

    def _handle_worker_done(self, stage: str, msg: dict[str, Any]) -> None:
        self.dispatcher.handle_worker_done(stage, msg)

    def _handle_run_level_message(
        self, stage: str, payload: dict[str, Any]
    ) -> None:
        self.dispatcher.handle_run_level_message(stage, payload)

    def _persist_done_side_effects(
        self, stage: str, chunk_id: str, payload: dict[str, Any]
    ) -> None:
        self.persister.persist_done_side_effects(stage, chunk_id, payload)

    def _persist_chunk_fields(
        self, stage: str, chunk_id: str, payload: dict[str, Any]
    ) -> None:
        self.persister.persist_chunk_fields(stage, chunk_id, payload)

    def _persist_lexicon_terms(self, terms: list[Any]) -> None:
        self.persister.persist_lexicon_terms(terms)

    def _persist_grammar_issues(self, chunk_id: str, issues: list[Any]) -> None:
        self.persister.persist_grammar_issues(chunk_id, issues)

    def _persist_qa_issues(self, chunk_id: str, issues: list[Any]) -> None:
        self.persister.persist_qa_issues(chunk_id, issues)

    def _persist_consistency_flags(
        self, chunk_id: str, flags: list[Any]
    ) -> None:
        self.persister.persist_consistency_flags(chunk_id, flags)

    def _promote_consistency_to_glossary(
        self, chunk_id: str, flags: list[dict[str, Any]]
    ) -> None:
        self.persister.promote_consistency_to_glossary(chunk_id, flags)

    def _forward_to_next_stage(
        self, next_stage: str, chunk_id: str, payload: dict[str, Any]
    ) -> None:
        self.persister.forward_to_next_stage(next_stage, chunk_id, payload)

    def _propagate_translation_fields(
        self,
        next_stage: str,
        payload: dict[str, Any],
        next_payload: dict[str, Any],
    ) -> None:
        self.persister._propagate_translation_fields(
            next_stage, payload, next_payload
        )

    def _attach_neighbour_chunks(
        self,
        stored: dict[str, Any],
        chunk_id: str,
        next_payload: dict[str, Any],
    ) -> None:
        self.persister._attach_neighbour_chunks(stored, chunk_id, next_payload)

    def _emit_artifact_if_assembler(
        self, stage: str, chunk_id: str, payload: dict[str, Any]
    ) -> None:
        self.persister._emit_artifact_if_assembler(stage, chunk_id, payload)

    def _emit_agent_done(
        self, stage: str, chunk_id: str, payload: dict[str, Any]
    ) -> None:
        self.persister._emit_agent_done(stage, chunk_id, payload)

    def _maybe_auto_assemble(self, payload: dict[str, Any]) -> None:
        self.persister._maybe_auto_assemble(payload)

    def _maybe_escalate(
        self,
        stage: str,
        next_stage: str | None,
        chunk_id: str,
        payload: dict[str, Any],
    ) -> str | None:
        return self.reflection.maybe_escalate(stage, next_stage, chunk_id, payload)

    def _reflection_threshold(self) -> float:
        return self.reflection.threshold()

    def _maybe_reflect(
        self, stage: str, chunk_id: str, payload: dict[str, Any]
    ) -> bool:
        return self.reflection.maybe_reflect(stage, chunk_id, payload)

    def _enqueue_reflection(
        self,
        chunk_id: str,
        payload: dict[str, Any],
        stored_chunk: dict[str, Any],
        score: float,
        reflection_count: int,
    ) -> None:
        self.reflection._enqueue_reflection(
            chunk_id, payload, stored_chunk, score, reflection_count
        )

    def _start_next_queued_project(self) -> None:
        self.queue.start_next()

    def remove_queued_project(self, project_id: str) -> bool:
        return self.queue.remove(project_id)

    # ------------------------------------------------------------------
    # drain loop
    # ------------------------------------------------------------------

    def _drain_loop(self) -> None:
        """Read every stage's output queue, update the store, forward chunks.

        Round-robin across stages with a soft back-pressure: when a queue
        is saturated (size >= MAX_DRAIN_PER_STAGE_PER_LOOP), drain up to
        that cap from it before moving on, so a chatty stage cannot
        starve quieter ones.

        All messages drained in a single cycle are processed within one
        SQLite transaction (via ``store.transaction()``) so that a crash
        mid-drain never leaves the store in an inconsistent state: either
        every message from the batch is persisted, or none are.

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
                batch: list[tuple[str, dict[str, Any]]] = []
                for _ in range(cap):
                    try:
                        msg = q.get_nowait()
                    except Exception:
                        break
                    batch.append((stage, msg))
                if not batch:
                    continue
                did_work = True
                try:
                    with self.store.transaction():
                        for st, msg in batch:
                            self.dispatcher.handle(st, msg)
                except Exception:
                    logger.exception(
                        "drain: atomic batch of %d messages failed; "
                        "transaction rolled back",
                        len(batch),
                    )
            if not did_work:
                # Watchdog: every iteration we check whether the
                # current project has been running without any new
                # event for too long. If so, emit a warning so the
                # user is not left staring at a frozen UI.
                self.watchdog.tick()
                time.sleep(0.05)

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

    # ------------------------------------------------------------------
    # assembler dispatch
    # ------------------------------------------------------------------

    def assemble_now(
        self,
        output_path: str | Path,
        fmt: str = "txt",
    ) -> dict[str, Any]:
        """Trigger the Assembler stage with the current set of chunks.

        Returns a summary dict. Errors are reported in the dict, not
        raised -- the caller (FastAPI) is request-scoped.
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
        stem = Path(proj.source_path).stem if proj.source_path else f"output_{proj.project_id[:8]}"
        out = out_dir / f"{stem}.{fmt}"
        self.assemble_now(out, fmt=fmt)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


__all__ = ["Orchestrator", "ProjectContext"]
