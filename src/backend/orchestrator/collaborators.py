"""Internal collaborators for ``Orchestrator``.

The orchestrator class used to hold 53 methods on a single class. After
the v4 split, those methods that belong to a focused responsibility
live here as small classes. The orchestrator owns them and exposes
matching thin delegates, so:

  * The public API (start, stop, submit_chunks, snapshot, ...) is
    unchanged.
  * The private API that the test suite uses (``_on_stage_done``,
    ``_reflection_threshold``, ``_start_next_queued_project``) is also
    unchanged -- the orchestrator keeps a delegate method that calls
    into the matching collaborator.

Each collaborator takes the orchestrator in its constructor. The
collaborator accesses shared state (``store``, ``_workers``, ``_lock``,
``_project``, ``_emit``, ...) through that reference. This is a
deliberate two-way link, not a Protocol: it is internal, it is testable
in isolation, and the alternative (passing 8 things to each
constructor) would be noisier without any real decoupling benefit.

The four collaborators extracted here:

  * ``ChunkPersister``        -- the persist_* family (6 methods).
  * ``MessageDispatcher``     -- the _handle_* family (7 methods).
  * ``ProjectQueue``          -- the sequential project queue (3 methods).
  * ``ReflectionController``  -- the reflection/escalation DAG (5 methods).

What stays on the orchestrator:
  * Lifecycle: ``start``, ``pause``, ``resume``, ``stop``, ``shutdown``.
  * Drain loop (``_drain_loop``) -- tight coupling to workers/lock/emit.
  * Hash verification (``_compute_source_hash``, ``_verify_chunk_hash``)
    -- called from many places; not a focused responsibility on its own.
  * Listeners / events (``add_listener``, ``remove_listener``, ``_emit``,
    ``snapshot``, ``recent_events``) -- cross-cutting concern, not a
    focus.
  * Assembler dispatch (``assemble_now``, ``maybe_auto_assemble``) --
    also small and self-contained; kept inline for now.
  * HITL handlers (``register_hltl``, ``respond_hltl``,
    ``replay_pending_hltl``, ``pending_hltl``) -- they touch both
    the store, the in-memory pending map, and worker queues; splitting
    them out is a future refactor.
"""
from __future__ import annotations

import json
import logging
import time
import uuid as _uuid
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .orchestrator import Orchestrator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ChunkPersister
# ---------------------------------------------------------------------------


class ChunkPersister:
    """Side effects that fire when a worker reports a stage done.

    Lives apart from the orchestrator so the dozens of ``_persist_*``
    methods are easy to scan as a group and so the field-update policy
    is in one place.
    """

    def __init__(self, orch: "Orchestrator"):
        self._orch = orch

    # -- public entry: called from _handle_worker_done --------------------

    def on_stage_done(
        self, stage: str, chunk_id: str | None, payload: dict[str, Any]
    ) -> None:
        if not chunk_id:
            return
        self._emit_artifact_if_assembler(stage, chunk_id, payload)
        self.persist_chunk_fields(stage, chunk_id, payload)
        self._emit_agent_done(stage, chunk_id, payload)
        self._maybe_auto_assemble(payload)
        if payload.get("terminal"):
            return
        next_stage = self._next_stage(stage)
        if next_stage is None or next_stage == self._orch.ASSEMBLER:
            return
        next_stage = self._orch.reflection.maybe_escalate(
            stage, next_stage, chunk_id, payload
        )
        if not self._orch.reflection.maybe_reflect(stage, chunk_id, payload):
            return
        self.forward_to_next_stage(next_stage, chunk_id, payload)

    # -- persist side effects on a per-stage basis -----------------------

    def persist_done_side_effects(
        self, stage: str, chunk_id: str, payload: dict[str, Any]
    ) -> None:
        if stage == "lexicon_builder" and payload.get("terms"):
            self.persist_lexicon_terms(payload.get("terms") or [])
        if stage == "terminology_researcher" and payload.get("suggestions"):
            self.persist_lexicon_terms(payload.get("suggestions") or [])
        if stage == "grammar_proofer" and payload.get("grammar_issues"):
            self.persist_grammar_issues(
                chunk_id, payload.get("grammar_issues") or []
            )
        if stage == "qa_validator" and payload.get("qa_issues"):
            self.persist_qa_issues(chunk_id, payload.get("qa_issues") or [])
        if stage == "consistency_checker" and payload.get("consistency_flags"):
            self.persist_consistency_flags(
                chunk_id, payload.get("consistency_flags") or []
            )
            self.promote_consistency_to_glossary(
                chunk_id, payload.get("consistency_flags") or []
            )

    def persist_lexicon_terms(self, terms: list[Any]) -> None:
        for term in terms:
            if isinstance(term, dict):
                # Normalise terminology_researcher output (uses "rationale" not "notes")
                if "rationale" in term and "notes" not in term:
                    term["notes"] = term["rationale"]
                try:
                    self._orch.store.upsert_lexicon_term(term)
                except Exception:
                    logger.exception("lexicon: failed to persist term")

    def promote_consistency_to_glossary(
        self, chunk_id: str, flags: list[dict[str, Any]]
    ) -> None:
        """Auto-promote high-confidence consistency flags to glossary entries.

        When a flag has confidence >= 0.6 and no lexicon term exists for that
        source term, create a low-confidence (0.3) lexicon entry.
        """
        for flag in flags:
            if not isinstance(flag, dict):
                continue
            source = flag.get("source_term", "")
            expected = flag.get("expected_translation", "")
            conf = float(flag.get("confidence", 0.0))
            if not source or not expected or conf < 0.6:
                continue
            existing = self._orch.store.find_lexicon_by_source(source)
            if existing is not None:
                continue  # already has a glossary entry
            self._orch.store.upsert_lexicon_term(
                {
                    "source": source,
                    "target": expected,
                    "category": "term",
                    "gender": "unknown",
                    "confidence": 0.3,
                    "notes": f"auto-extracted from consistency flag in chunk {chunk_id}",
                    "evidence_refs": [f"chunk:{chunk_id}"],
                    "chapter_id": None,
                }
            )
            logger.info(
                "glossary: auto-promoted consistency flag '%s'->'%s' (conf=%.1f)",
                source, expected, conf,
            )

    def persist_grammar_issues(self, chunk_id: str, issues: list[Any]) -> None:
        for issue in issues:
            if not isinstance(issue, dict):
                continue
            try:
                self._orch.store.add_grammar_issue(
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

    def persist_qa_issues(self, chunk_id: str, issues: list[Any]) -> None:
        for issue in issues:
            if not isinstance(issue, dict):
                continue
            try:
                self._orch.store.add_qa_issue(
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

    def persist_consistency_flags(self, chunk_id: str, flags: list[Any]) -> None:
        for flag in flags:
            if not isinstance(flag, dict):
                continue
            try:
                self._orch.store.add_consistency_flag(
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

    # -- chunk field writes ---------------------------------------------

    def persist_chunk_fields(
        self, stage: str, chunk_id: str, payload: dict[str, Any]
    ) -> None:
        for field_name in (
            "raw_translation",
            "glossary_applied",
            "llm_refined",
            "qa_checked",
            "grammar_checked",
            "polished_translation",
        ):
            if field_name in payload:
                self._orch.store.update_chunk_field(
                    chunk_id, field_name, payload[field_name]
                )
        if "review_score" in payload:
            self._orch.store.update_chunk_field(
                chunk_id, "review_score", payload["review_score"]
            )
        if "review_annotations" in payload:
            self._orch.store.update_chunk_field(
                chunk_id,
                "review_annotations",
                json.dumps(payload["review_annotations"], ensure_ascii=False),
            )
        new_status = (
            payload.get("status")
            or self._orch.STAGE_TO_STATUS.get(stage, "parsed")
        )
        self._orch.store.update_chunk_field(chunk_id, "status", new_status)

    # -- forward chunks down the pipeline --------------------------------

    def forward_to_next_stage(
        self, next_stage: str, chunk_id: str, payload: dict[str, Any]
    ) -> None:
        from ..agents.base_worker import make_task_message

        action = payload.get("action") or self._orch._default_action_for(next_stage)
        next_payload = dict(payload.get("next_payload") or {})

        self._propagate_translation_fields(next_stage, payload, next_payload)

        # Verify source hash integrity before forwarding.
        stored = self._orch.store.get_chunk(chunk_id) or {}
        src_text = stored.get("source_text") or ""
        src_hash = stored.get("source_hash")
        if not self._orch._verify_chunk_hash(chunk_id, src_text, src_hash):
            return

        for key in (
            "source_text",
            "chapter_id",
            "chapter_title",
            "source_lang",
            "target_lang",
            "raw_translation",
            "glossary_applied",
            "llm_refined",
            "qa_checked",
            "grammar_checked",
            "polished_translation",
            "review_score",
            "review_annotations",
        ):
            if key in stored and key not in next_payload:
                next_payload[key] = stored[key]

        ctx = self._orch._project
        if ctx is not None:
            next_payload.setdefault("source_lang", ctx.source_lang)
            next_payload.setdefault("target_lang", ctx.target_lang)

        if next_stage == "glossary_applier":
            next_payload["lexicon_terms"] = self._orch.store.list_lexicon()
        if next_stage == "llm_refiner":
            next_payload["lexicon_terms"] = self._orch.store.list_lexicon()
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

        self._orch._workers.queues_for(next_stage).input.put(
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
            "llm_refiner",
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
            "llm_refined",
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
        neighbour_chunks = self._orch.store.list_chunks(chapter_id=chap, limit=20)
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

    # -- helpers used by on_stage_done -----------------------------------

    def _emit_artifact_if_assembler(
        self, stage: str, chunk_id: str, payload: dict[str, Any]
    ) -> None:
        if stage != self._orch.ASSEMBLER:
            return
        if not payload.get("output_path"):
            return
        artifact = {
            "output_path": payload.get("output_path"),
            "chunk_count": payload.get("chunk_count", 0),
            "created_at": self._orch._now_iso(),
        }
        self._orch.store.set_state("output_artifact", artifact)
        with self._orch._lock:
            if self._orch._project is not None:
                self._orch._project.status = "done"
        self._orch._emit({"type": "artifact_ready", **artifact})
        # The project is finished on the backend side. If the user
        # queued additional files via POST /projects, start the next
        # one now so the whole batch runs ``a la file`` without the
        # GUI having to poll.
        self._orch.queue.start_next()

    def _emit_agent_done(
        self, stage: str, chunk_id: str, payload: dict[str, Any]
    ) -> None:
        self._orch._emit(
            {
                "type": "agent_done",
                "stage": stage,
                "chunk_id": chunk_id,
                "payload": payload,
            }
        )

    def _maybe_auto_assemble(self, payload: dict[str, Any]) -> None:
        threshold_status = self._orch._penultimate_status()
        if not threshold_status or payload.get("status") != threshold_status:
            return
        try:
            self._orch.maybe_auto_assemble()
        except Exception:
            logger.exception("auto-assemble dispatch failed")

    def _next_stage(self, stage: str) -> str | None:
        return self._orch._next_stage(stage)


# ---------------------------------------------------------------------------
# MessageDispatcher
# ---------------------------------------------------------------------------


class MessageDispatcher:
    """Dispatches messages drained from worker output queues.

    Replaces the ``_handle_worker_*`` family. Kept as its own object
    because the dispatch table (``_WORKER_MSG_DISPATCH``) and the
    parser's run-level completion are tightly related concerns that
    are independent of the orchestrator's lifecycle.
    """

    _DISPATCH = {
        "error": "handle_worker_error",
        "hltl_request": "handle_worker_hltl_request",
        "progress": "handle_worker_progress",
        "run_done": "handle_worker_run_done",
        "done": "handle_worker_done",
    }

    def __init__(self, orch: "Orchestrator"):
        self._orch = orch

    def handle(self, stage: str, msg: dict[str, Any]) -> None:
        msg_type = msg.get("type")
        handler_name = self._DISPATCH.get(msg_type)
        if handler_name is None:
            logger.debug("Unhandled message from %s: %r", stage, msg)
            return
        getattr(self, handler_name)(stage, msg)

    def handle_worker_error(self, stage: str, msg: dict[str, Any]) -> None:
        chunk_id = msg.get("chunk_id")
        payload = msg.get("payload") or {}
        logger.error(
            "[%s] error on chunk %s: %s",
            stage,
            chunk_id,
            payload.get("message"),
        )
        if chunk_id:
            self._orch.store.update_chunk_field(chunk_id, "status", self._orch.STATUS_ERROR)
            self._orch.store.update_chunk_field(
                chunk_id, "error_message", payload.get("message")
            )
        self._orch._emit(
            {
                "type": "agent_error",
                "stage": stage,
                "chunk_id": chunk_id,
                "payload": payload,
            }
        )
        # Project-level errors (chunk_id is None) end the project. If
        # the user queued additional files, start the next one so
        # the queue does not stall on a single bad file.
        if chunk_id is None:
            with self._orch._lock:
                if self._orch._project is not None:
                    self._orch._project.status = "error"
            self._orch.queue.start_next()

    def handle_worker_hltl_request(self, stage: str, msg: dict[str, Any]) -> None:
        self._orch.register_hltl(msg)

    def handle_worker_progress(self, stage: str, msg: dict[str, Any]) -> None:
        chunk_id = msg.get("chunk_id")
        payload = msg.get("payload") or {}
        base = {
            "stage": stage,
            "chunk_id": chunk_id,
            "percent": payload.get("percent"),
            "note": payload.get("note"),
        }
        self._orch._emit({"type": "agent_progress", **base})
        self._orch._emit({"type": "stage_progress", **base})
        if chunk_id:
            self._orch._emit({"type": "chunk_progress", **base})

    def handle_worker_run_done(self, stage: str, msg: dict[str, Any]) -> None:
        payload = msg.get("payload") or {}
        self.handle_run_level_message(stage, payload)

    def handle_worker_done(self, stage: str, msg: dict[str, Any]) -> None:
        chunk_id = msg.get("chunk_id")
        payload = msg.get("payload") or {}
        # run_done is a project-level completion (chunk_id=None). Any
        # stage may emit it when it finishes its run-level work; we
        # delegate to a dedicated handler.
        if chunk_id is None:
            self.handle_run_level_message(stage, payload)
            return
        self._orch.persister.persist_done_side_effects(stage, chunk_id, payload)
        self._orch.persister.on_stage_done(stage, chunk_id, payload)

    def handle_run_level_message(
        self, stage: str, payload: dict[str, Any]
    ) -> None:
        """Process a project-level (chunk_id=None) completion message.

        Currently only the Parser uses this path: it produces a manifest
        and a list of chapters/chunks that must be injected into the
        FastTranslator queue (the regular forward path can't do it
        because the Parser's ``terminal=True`` flag would block it).
        """
        if stage == self._orch.PARSER:
            if payload.get("manifest_path"):
                self._orch.store.set_state(
                    "project_manifest_path", payload["manifest_path"]
                )
            if payload.get("target_path"):
                self._orch.store.set_state("target_path", payload["target_path"])
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
                self._orch.submit_chunks(flat)
                logger.info(
                    "orchestrator: parser injected %d chunks into the pipeline; next=%s",
                    len(flat),
                    "fast_translator",
                )
            self._orch._emit(
                {
                    "type": "agent_done",
                    "stage": stage,
                    "chunk_id": None,
                    "payload": payload,
                }
            )
            self._orch._emit(
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
        self._orch._emit(
            {
                "type": "agent_done",
                "stage": stage,
                "chunk_id": None,
                "payload": payload,
            }
        )


# ---------------------------------------------------------------------------
# ProjectQueue
# ---------------------------------------------------------------------------


class ProjectQueue:
    """Sequential project queue.

    When ``Orchestrator.start`` is called while a project is already
    running, the new project is appended here and the orchestrator
    picks it up automatically once the current project finishes
    (assembler done). Stays in its own class because it has its own
    state (``_items``) and three small methods, and because tests poke
    at it (``orch.remove_queued_project``) -- keeping that contract
    isolated makes the public surface obvious.
    """

    def __init__(self, orch: "Orchestrator"):
        self._orch = orch
        self._items: list[Any] = []

    def append(self, project: Any) -> None:
        self._items.append(project)
        self._orch._emit({
            "type": "project_queued",
            "project_id": project.project_id,
            "queue_position": len(self._items),
        })

    def is_empty(self) -> bool:
        return not self._items

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

    def clear(self) -> None:
        self._items.clear()

    def remove(self, project_id: str) -> bool:
        """Drop a queued project by id. Returns True if removed.

        Only projects that have not started yet can be removed.
        The currently-running project is left untouched; the user
        must hit Stop to cancel it. The endpoint returns 409 in
        that case so the GUI can surface a clear error.
        """
        for i, proj in enumerate(self._items):
            if proj.project_id == project_id:
                self._items.pop(i)
                logger.info(
                    "queue: removed project %s (was at position %d)",
                    project_id, i + 1,
                )
                return True
        return False

    def start_next(self) -> None:
        """Pop the next queued project and start it. No-op if empty.

        Called by ``_emit_artifact_if_assembler`` once the
        current project has been written to disk by the
        Assembler. Also called by ``stop()`` so a manual stop
        does not strand pending projects in the queue.
        """
        with self._orch._lock:
            if not self._items:
                return
            # Refuse to start a new project if the user paused.
            if self._orch._project and self._orch._project.status == "paused":
                return
            next_project = self._items.pop(0)
            # ``start`` will set self._project and re-spawn the
            # workers for the new project's profile / source.
            self._orch._emit({
                "type": "project_started_from_queue",
                "project_id": next_project.project_id,
                "queue_remaining": len(self._items),
            })
        # Call start without holding the lock to avoid re-entrancy
        # in WorkerManager.
        try:
            self._orch.start(next_project)
        except Exception:
            logger.exception(
                "queue: failed to start next project %s",
                next_project.project_id,
            )
            self._orch._emit({
                "type": "project_queue_failed",
                "project_id": next_project.project_id,
            })


# ---------------------------------------------------------------------------
# ReflectionController
# ---------------------------------------------------------------------------


class ReflectionController:
    """Reflection / escalation policy for the DAG.

    Centralises two things:
      * The DAG shortcuts (qa_clean -> skip grammar; consistency flag
        on premium -> terminology).
      * The reflection loop (reviewer score below threshold -> re-run
        llm_polisher, max 2 times, then escalate to HITL).
    """

    # Profile-specific reflection thresholds. Eco has no reviewer at all.
    REFLEXION_THRESHOLD: dict[str, float] = {
        "eco": 0.0,  # reviewer not used
        "balanced": 0.7,
        "premium": 0.85,
    }

    def __init__(self, orch: "Orchestrator"):
        self._orch = orch

    def threshold(self) -> float:
        """Return the review-score threshold below which a reflection is triggered."""
        profile = (
            self._orch._project.profile
            if self._orch._project is not None
            else "balanced"
        )
        return self.REFLEXION_THRESHOLD.get(profile, 0.7)

    def maybe_escalate(
        self,
        stage: str,
        next_stage: str | None,
        chunk_id: str,
        payload: dict[str, Any],
    ) -> str | None:
        """Apply DAG shortcuts and escalation policies.

        Current policies:
          * qa_clean + balanced/premium -> skip grammar_proofer to reviewer.
          * consistency flag on premium profile -> branch to terminology_researcher.
          * qa_issues on any profile -> keep grammar_proofer (do not skip).
        """
        if next_stage is None:
            return None
        order = self._orch._stage_order
        profile = (
            self._orch._project.profile
            if self._orch._project is not None
            else "balanced"
        )

        # Policy A: clean QA can bypass grammar_proofer in balanced/premium.
        if stage == "qa_validator" and next_stage == "grammar_proofer":
            if profile in ("balanced", "premium") and not payload.get("qa_issues"):
                if "reviewer" in order:
                    self._orch._emit(
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
                self._orch._emit(
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

    def maybe_reflect(
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
        threshold = self.threshold()
        if score >= threshold:
            return True
        stored_chunk = self._orch.store.get_chunk(chunk_id) or {}
        stored_meta = dict(stored_chunk.get("metadata") or {})
        reflection_count = int(stored_meta.get("reflection_count") or 0)
        max_reflections = 2
        if reflection_count >= max_reflections:
            self._orch._emit(
                {
                    "type": "reflection_exhausted",
                    "chunk_id": chunk_id,
                    "score": score,
                    "reflection_count": reflection_count,
                }
            )
            self._orch.register_hltl(
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
        self._orch.store.update_chunk_field(
            chunk_id,
            "metadata_json",
            json.dumps(stored_meta, ensure_ascii=False),
        )
        self._enqueue_reflection(
            chunk_id, payload, stored_chunk, score, reflection_count
        )
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
                f"[{a.get('type', '')}] {a.get('span', '')} -> {a.get('suggestion', '')}"
                for a in annotations[:5]
            )
            if annotations
            else ""
        )
        src_for_reflect = (
            payload.get("source_text")
            or stored_chunk.get("source_text")
            or ""
        )
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
        self._orch._workers.queues_for("llm_polisher").input.put(
            make_task_message(
                chunk_id=chunk_id,
                action="polish",
                payload=reflection_payload,
            )
        )
        self._orch._emit(
            {
                "type": "reflection_triggered",
                "chunk_id": chunk_id,
                "score": score,
                "reflection_count": reflection_count,
            }
        )


# ---------------------------------------------------------------------------
# Watchdog -- the 90s stall detector.
# ---------------------------------------------------------------------------


class Watchdog:
    """Tracks last-progress timestamp and emits ``pipeline_stalled`` events.

    Pulled out of the drain loop so the loop body stays focused on
    queue draining. The watchdog state is owned by the orchestrator
    (``_last_progress_at`` / ``_last_stall_warn_at``); this class only
    reads it and emits the event.
    """

    STALL_THRESHOLD_SEC = 90.0
    WARN_REPEAT_SEC = 30.0

    def __init__(self, orch: "Orchestrator"):
        self._orch = orch

    def tick(self) -> None:
        now = time.time()
        project = self._orch._project
        if (
            project
            and project.status == "running"
            and (now - self._orch._last_progress_at) > self.STALL_THRESHOLD_SEC
            and (now - self._orch._last_stall_warn_at) > self.WARN_REPEAT_SEC
        ):
            self._orch._last_stall_warn_at = now
            idle = int(now - self._orch._last_progress_at)
            logger.warning(
                "pipeline stalled: no event for %ds on project %s",
                idle, project.project_id,
            )
            self._orch._emit({
                "type": "pipeline_stalled",
                "idle_seconds": idle,
                "project_id": project.project_id,
            })
