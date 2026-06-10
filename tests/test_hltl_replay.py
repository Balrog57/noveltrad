"""Tests for the HITL persistence + replay behaviour.

Covers the orchestrator-defects fix:

  * (a) `respond_hltl` emits `hltl_unroutable` (and does NOT flip the
    chunk back to `parsed`) when the target stage has no live worker.
  * (b) Once a worker for the target stage is alive again,
    `replay_pending_hltl` re-injects the chunk and flips it to `parsed`.
  * (c) `pending_hltl` rows survive a StateStore close/reopen (i.e.
    crash-safe persistence).
"""

import tempfile
import threading
import time
import unittest
import uuid
from pathlib import Path
from typing import Any


from src.backend.orchestrator.orchestrator import Orchestrator
from src.backend.orchestrator.state_store import StateStore
from src.backend.orchestrator.worker_manager import WorkerManager
from src.backend.orchestrator.pipeline import (
    DEFAULT_PIPELINE_ORDER,
    PARSER,
    FAST_TRANSLATOR,
)


class _FakeWorkerManager:
    """Same surface as `tests.test_orchestrator_drain.FakeWorkerManager`
    but kept local to avoid cross-test imports.
    """

    def __init__(self, stages):
        self._stages = stages
        self._queues: dict[str, "_FakeStageQueues"] = {}
        self._alive: set[str] = set()
        self._lock = threading.RLock()
        self._on_worker_exit = None

    def set_exit_hook(self, hook):
        self._on_worker_exit = hook

    def queues_for(self, stage: str) -> "_FakeStageQueues":
        with self._lock:
            if stage not in self._queues:
                self._queues[stage] = _FakeStageQueues(stage)
            return self._queues[stage]

    def is_alive(self, stage: str) -> bool:
        return stage in self._alive

    def start_stage(self, stage: str, count=None) -> None:
        with self._lock:
            self._alive.add(stage)
            self.queues_for(stage)

    def pause_stage(self, stage: str) -> None:
        pass

    def resume_stage(self, stage: str) -> None:
        pass

    def shutdown_stage(self, stage: str) -> None:
        with self._lock:
            self._alive.discard(stage)

    def shutdown(self, timeout=5.0) -> None:
        with self._lock:
            for q in self._queues.values():
                q.close()
            self._alive.clear()

    def snapshot(self):
        return {}


class _FakeStageQueues:
    def __init__(self, stage: str):
        self.stage = stage
        self.input = _FakeQueue()
        self.output = _FakeQueue()

    def close(self) -> None:
        self.input.close()
        self.output.close()


class _FakeQueue:
    def __init__(self):
        self._items = []
        self._lock = threading.Lock()

    def put(self, item, block=True, timeout=None):
        with self._lock:
            self._items.append(item)

    def get_nowait(self):
        from queue import Empty

        with self._lock:
            if not self._items:
                raise Empty()
            return self._items.pop(0)

    def qsize(self) -> int:
        with self._lock:
            return len(self._items)

    def close(self) -> None:
        with self._lock:
            self._items.clear()


class HltlReplayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.store = StateStore(self.tmp / "state.db")
        self.orch = Orchestrator(self.store)
        self.fake = _FakeWorkerManager(self.orch._stages)
        self.orch._workers = self.fake
        # All stages start as alive by default.
        for stage in DEFAULT_PIPELINE_ORDER:
            self.fake.start_stage(stage)
        # Seed a chunk in the store so we can observe status transitions.
        self.chunk_id = uuid.uuid4().hex
        self.store.add_chunk(
            {
                "id": self.chunk_id,
                "chapter_id": "ch1",
                "chapter_title": "Chapter 1",
                "chunk_index": 0,
                "source_text": "Hello world.",
                "status": "parsed",
            }
        )

    def tearDown(self) -> None:
        self.fake.shutdown()
        self.store.close()

    def _make_hltl_request(self, stage: str = "qa_validator") -> str:
        """Drive `register_hltl` and return the request_id."""
        events: list[dict] = []
        cond = threading.Condition()
        self.orch.add_listener(lambda e: events.append(e))
        try:
            self.orch.register_hltl(
                {
                    "type": "hltl_request",
                    "stage": stage,
                    "chunk_id": self.chunk_id,
                    "payload": {"issue": {"summary": "ambiguous term"}},
                }
            )
            deadline = time.time() + 2.0
            while time.time() < deadline:
                with cond:
                    pass
                if any(e.get("type") == "hltl_alert" for e in events):
                    break
                time.sleep(0.02)
            pending = self.store.list_unresolved_hltl()
            self.assertEqual(len(pending), 1)
            return pending[0]["request_id"]
        finally:
            self.orch._listeners.clear()

    def test_a_worker_dead_keeps_chunk_waiting(self) -> None:
        request_id = self._make_hltl_request(stage="qa_validator")
        # Kill the qa_validator worker BEFORE we respond.
        self.fake.shutdown_stage("qa_validator")
        unroutable: list[dict] = []
        cond = threading.Condition()

        def listener(e):
            if e.get("type") == "hltl_unroutable":
                with cond:
                    unroutable.append(e)
                    cond.notify_all()

        self.orch.add_listener(listener)
        try:
            ok = self.orch.respond_hltl(request_id, "yes")
            with cond:
                cond.wait_for(lambda: bool(unroutable), timeout=2.0)
            self.assertTrue(ok, "respond_hltl should still succeed in routing attempt")
            self.assertEqual(len(unroutable), 1)
            self.assertEqual(unroutable[0]["reason"], "worker_dead")
            chunk = self.store.get_chunk(self.chunk_id)
            self.assertEqual(chunk["status"], "waiting_for_human")
        finally:
            self.orch._listeners.clear()

    def test_b_replay_after_worker_revival(self) -> None:
        request_id = self._make_hltl_request(stage="qa_validator")
        # Round 1: worker dead, respond returns hltl_unroutable.
        self.fake.shutdown_stage("qa_validator")
        self.orch.respond_hltl(request_id, "yes")
        # Round 2: bring the worker back, then replay.
        self.fake.start_stage("qa_validator")
        # Drop the in-memory copy so replay must load from store.
        with self.orch._lock:
            self.orch._pending_hltl.pop(request_id, None)
        routed = self.orch.replay_pending_hltl()
        self.assertEqual(routed["routed"], 1, "replay should re-inject the chunk")
        chunk = self.store.get_chunk(self.chunk_id)
        self.assertEqual(chunk["status"], "parsed")
        # The QA validator input queue should have received one message.
        q = self.fake.queues_for("qa_validator").input
        self.assertEqual(q.qsize(), 1)

    def test_c_persistence_across_restart(self) -> None:
        request_id = self._make_hltl_request(stage="qa_validator")
        # Persist + drop the in-memory cache.
        self.fake.shutdown_stage("qa_validator")
        with self.orch._lock:
            self.orch._pending_hltl.clear()
        # Tear down the orchestrator + store.
        self.fake.shutdown()
        self.store.close()
        # Re-open the same SQLite file and re-create the orchestrator.
        store2 = StateStore(self.tmp / "state.db")
        orch2 = Orchestrator(store2)
        fake2 = _FakeWorkerManager(orch2._stages)
        orch2._workers = fake2
        for stage in DEFAULT_PIPELINE_ORDER:
            fake2.start_stage(stage)
        try:
            pending = store2.list_unresolved_hltl()
            self.assertEqual(len(pending), 1)
            self.assertEqual(pending[0]["request_id"], request_id)
            routed = orch2.replay_pending_hltl()
            self.assertEqual(routed["routed"], 1)
            chunk = store2.get_chunk(self.chunk_id)
            self.assertEqual(chunk["status"], "parsed")
        finally:
            fake2.shutdown()
            store2.close()


if __name__ == "__main__":
    unittest.main()
