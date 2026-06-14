import tempfile
import threading
import unittest
from pathlib import Path
from typing import Any

from src.backend.orchestrator.orchestrator import Orchestrator, ProjectContext
from src.backend.orchestrator.state_store import StateStore


class _FakeWorkerManager:
    def __init__(self, stages: dict[str, Any]):
        self._stages = stages
        self._queues: dict[str, _FakeStageQueues] = {}
        self._alive: set[str] = set()
        self._lock = threading.RLock()

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

    def shutdown(self, timeout: float = 5.0) -> None:
        self._alive.clear()

    def snapshot(self) -> dict[str, Any]:
        return {}


class _FakeStageQueues:
    def __init__(self, stage: str):
        self.stage = stage
        self.input = _FakeQueue()
        self.output = _FakeQueue()


class _FakeQueue:
    def __init__(self):
        self.items: list[Any] = []

    def put(self, item, block: bool = True, timeout=None):
        self.items.append(item)

    def qsize(self) -> int:
        return len(self.items)


def _build_orchestrator(tmp: Path, profile: str = "balanced") -> Orchestrator:
    store = StateStore(tmp / "state.db")
    orch = Orchestrator(store)
    orch._workers = _FakeWorkerManager(orch._stages)
    orch._project = ProjectContext(
        project_id="p1",
        project_dir=tmp,
        source_lang="en",
        target_lang="fr",
        source_path=tmp / "source.txt",
        profile=profile,
    )
    for stage in orch._stage_order:
        orch._workers.start_stage(stage)
    return orch


def _add_chunk(orch: Orchestrator, metadata: dict[str, Any] | None = None) -> str:
    chunk_id = "chunk-1"
    orch.store.add_chunk(
        {
            "id": chunk_id,
            "chapter_id": "ch1",
            "chapter_title": "Chapter 1",
            "chunk_index": 0,
            "source_text": "Hello world",
            "source_hash": None,
            "raw_translation": "Bonjour monde",
            "grammar_checked": "Bonjour le monde",
            "polished_translation": "Bonjour le monde.",
            "metadata": metadata or {},
        }
    )
    return chunk_id


class ReflectionLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_obj = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmp_obj.name)

    def tearDown(self) -> None:
        self.tmp_obj.cleanup()

    def test_reflection_thresholds_by_profile(self) -> None:
        cases = {"eco": 0.0, "balanced": 0.7, "premium": 0.85}
        for profile, expected in cases.items():
            orch = _build_orchestrator(self.tmp, profile=profile)
            try:
                self.assertEqual(orch._reflection_threshold(), expected)
            finally:
                orch.store.close()

    def test_low_review_score_requeues_polisher_and_stops_forwarding(self) -> None:
        orch = _build_orchestrator(self.tmp, profile="balanced")
        events: list[dict[str, Any]] = []
        orch.add_listener(events.append)
        try:
            chunk_id = _add_chunk(orch)
            orch._on_stage_done(
                "reviewer",
                chunk_id,
                {
                    "review_score": 0.2,
                    "review_annotations": [
                        {
                            "type": "style",
                            "span": "Bonjour",
                            "suggestion": "Improve tone",
                        }
                    ],
                    "polished_translation": "Bonjour le monde.",
                },
            )
            polisher_q = orch._workers.queues_for("llm_polisher").input
            self.assertEqual(polisher_q.qsize(), 1)
            task = polisher_q.items[0]
            self.assertEqual(task["action"], "polish")
            self.assertEqual(task["payload"]["reflection_count"], 1)
            stored = orch.store.get_chunk(chunk_id) or {}
            self.assertEqual(stored.get("metadata", {}).get("reflection_count"), 1)
            self.assertIn("reflection_triggered", [e.get("type") for e in events])
        finally:
            orch.store.close()

    def test_reflection_exhaustion_registers_hltl(self) -> None:
        orch = _build_orchestrator(self.tmp, profile="premium")
        events: list[dict[str, Any]] = []
        orch.add_listener(events.append)
        try:
            chunk_id = _add_chunk(orch, metadata={"reflection_count": 2})
            orch._on_stage_done(
                "reviewer",
                chunk_id,
                {
                    "review_score": 0.3,
                    "review_annotations": [],
                    "polished_translation": "Bonjour le monde.",
                },
            )
            self.assertIn("reflection_exhausted", [e.get("type") for e in events])
            pending = orch.store.list_unresolved_hltl()
            self.assertEqual(len(pending), 1)
            self.assertEqual(pending[0]["chunk_id"], chunk_id)
            self.assertEqual(pending[0]["stage"], "reviewer")
            self.assertEqual(
                pending[0]["issue"].get("kind"), "reflection_exhausted"
            )
        finally:
            orch.store.close()


if __name__ == "__main__":
    unittest.main()
