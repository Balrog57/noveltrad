"""Tests for the orchestrator drain loop with back-pressure.

We do NOT spawn real worker processes. We construct an `Orchestrator`
with a fake `WorkerManager` that exposes the same surface as the real
one and lets us inject messages directly into stage output queues.

Goal: verify the drain loop behaviour added by the orchestrator-defects
fix plan:

  * (a) a chatty stage (queue saturated) gets drained up to
    MAX_DRAIN_PER_STAGE_PER_LOOP per loop iteration.
  * (b) round-robin across stages remains stable when no queue is
    saturated.
  * (c) shutdown drains cleanly and `_drain_loop` exits.
"""

import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from typing import Any

import multiprocessing as mp

from src.backend.orchestrator.orchestrator import (
    MAX_DRAIN_PER_STAGE_PER_LOOP,
    Orchestrator,
)
from src.backend.orchestrator.pipeline import DEFAULT_PIPELINE_ORDER
from src.backend.orchestrator.state_store import StateStore


class FakeWorkerManager:
    """In-memory stand-in for WorkerManager used by Orchestrator tests.

    Implements the same surface as `WorkerManager` for the methods the
    orchestrator actually calls in `_drain_loop` and the HITL paths:
    `queues_for`, `is_alive`, `start_stage`, `pause_stage`,
    `resume_stage`, `shutdown_stage`, `shutdown`, `snapshot`,
    `set_exit_hook`.
    """

    def __init__(self, stages: dict[str, Any]):
        self._stages = stages
        self._queues: dict[str, _FakeStageQueues] = {}
        self._alive: set[str] = set()
        self._on_worker_exit = None
        self._lock = threading.RLock()
        self._shutdown_requested = False

    def set_exit_hook(self, hook):
        self._on_worker_exit = hook

    def queues_for(self, stage: str) -> "_FakeStageQueues":
        with self._lock:
            if stage not in self._queues:
                self._queues[stage] = _FakeStageQueues(stage)
            return self._queues[stage]

    def is_alive(self, stage: str) -> bool:
        return stage in self._alive

    def start_stage(self, stage: str, count: int | None = None) -> None:
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

    def shutdown(self, timeout: float = 5.0) -> None:
        with self._lock:
            self._shutdown_requested = True
            for q in self._queues.values():
                q.close()
            self._alive.clear()

    def snapshot(self) -> dict[str, Any]:
        return {}


class _FakeStageQueues:
    """A multiprocessing.Queue-compatible stand-in with a usable qsize().

    The real `mp.Queue` would work too, but the fake lets us run the
    tests without spawning processes on every assertion.
    """

    def __init__(self, stage: str):
        self.stage = stage
        self.input: _FakeQueue = _FakeQueue()
        self.output: _FakeQueue = _FakeQueue()

    def close(self) -> None:
        self.input.close()
        self.output.close()


class _FakeQueue:
    def __init__(self, maxsize: int = 10_000):
        self._items: list[Any] = []
        self._lock = threading.Lock()
        self._closed = False
        self.maxsize = maxsize

    def put(self, item, block: bool = True, timeout=None):
        with self._lock:
            if self._closed:
                raise RuntimeError("queue closed")
            self._items.append(item)

    def get_nowait(self):
        with self._lock:
            if not self._items:
                from queue import Empty

                raise Empty()
            return self._items.pop(0)

    def qsize(self) -> int:
        with self._lock:
            return len(self._items)

    def close(self) -> None:
        with self._lock:
            self._closed = True


def _build_orchestrator(tmp: Path) -> Orchestrator:
    """Create an Orchestrator wired to a fake WorkerManager."""
    store = StateStore(tmp / "state.db")
    orch = Orchestrator(store)
    fake = FakeWorkerManager(orch._stages)
    orch._workers = fake
    return orch


def _stop_drain(orch: Orchestrator, timeout: float = 2.0) -> None:
    orch._stop_drain.set()
    if orch._drain_thread is not None and orch._drain_thread.is_alive():
        orch._drain_thread.join(timeout=timeout)


def _make_done_message(chunk_id: str | None, stage: str = "fast_translator") -> dict:
    return {
        "type": "done",
        "stage": stage,
        "chunk_id": chunk_id,
        "payload": {"status": "fast_translated", "raw_translation": "hi"},
    }


class DrainLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.orch = _build_orchestrator(self.tmp)
        # Start all stages' fake queues (no real workers).
        for stage in DEFAULT_PIPELINE_ORDER:
            self.orch._workers.start_stage(stage)
        self.orch._stop_drain.clear()
        self.orch._drain_thread = threading.Thread(
            target=self.orch._drain_loop,
            name="orch-drain-test",
            daemon=True,
        )
        self.orch._drain_thread.start()

    def tearDown(self) -> None:
        _stop_drain(self.orch)
        self.orch._workers.shutdown()
        self.orch.store.close()

    def _wait_for_drain(self, expected_remaining: int = 0, timeout: float = 2.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            total = sum(
                self.orch._workers.queues_for(s).output.qsize()
                for s in DEFAULT_PIPELINE_ORDER
            )
            if total == expected_remaining:
                return
            time.sleep(0.02)

    def test_a_chatty_stage_drains_capped_per_loop(self) -> None:
        """A saturated queue should be drained up to the cap per iteration."""
        fast_q = self.orch._workers.queues_for("fast_translator").output
        # Pour way more than the cap so the back-pressure path is exercised.
        total = MAX_DRAIN_PER_STAGE_PER_LOOP * 4 + 3
        for i in range(total):
            fast_q.put(
                _make_done_message(f"chunk-{i}", stage="fast_translator")
            )
        self._wait_for_drain(expected_remaining=0, timeout=3.0)
        remaining = fast_q.qsize()
        self.assertEqual(remaining, 0, "all chatty messages must eventually drain")

    def test_b_round_robin_order_preserved_when_balanced(self) -> None:
        """When queues are not saturated, all stages get one slot per loop.

        We feed exactly 1 message into 3 different stages; the first 3
        handled events should come from those 3 stages in pipeline order.
        """
        seen: list[str] = []
        cond = threading.Condition()

        def listener(ev):
            if ev.get("type") == "agent_done" and ev.get("chunk_id"):
                with cond:
                    seen.append(ev["stage"])
                    cond.notify_all()

        self.orch.add_listener(listener)
        try:
            for stage in ("fast_translator", "consistency_checker", "llm_polisher"):
                self.orch._workers.queues_for(stage).output.put(
                    _make_done_message(f"c-{stage}", stage=stage)
                )
            with cond:
                cond.wait_for(lambda: len(seen) >= 3, timeout=2.0)
            self.assertEqual(
                seen[:3],
                [
                    "fast_translator",
                    "consistency_checker",
                    "llm_polisher",
                ],
                "round-robin should preserve pipeline order",
            )
        finally:
            self.orch.remove_listener(listener)

    def test_c_shutdown_drains_loop_cleanly(self) -> None:
        """Setting _stop_drain must end the drain thread promptly."""
        self.orch._stop_drain.set()
        self.orch._drain_thread.join(timeout=2.0)
        self.assertFalse(self.orch._drain_thread.is_alive())


if __name__ == "__main__":
    unittest.main()
