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


def _build_orchestrator(tmp: Path, profile: str) -> Orchestrator:
    store = StateStore(tmp / f"{profile}.db")
    orch = Orchestrator(store)
    orch._workers = _FakeWorkerManager(orch._stages)
    orch._project = ProjectContext(
        project_id=f"p-{profile}",
        project_dir=tmp,
        source_lang="en",
        target_lang="fr",
        source_path=tmp / "source.txt",
        profile=profile,
    )
    for stage in orch._stage_order:
        orch._workers.start_stage(stage)
    return orch


def _add_chunk(orch: Orchestrator, chunk_id: str = "chunk-1") -> str:
    orch.store.add_chunk(
        {
            "id": chunk_id,
            "chapter_id": "ch1",
            "chapter_title": "Chapter 1",
            "chunk_index": 0,
            "source_text": "Hello world",
            "source_hash": None,
            "raw_translation": "Bonjour monde",
            "glossary_applied": "Bonjour monde",
            "qa_checked": "Bonjour monde",
        }
    )
    return chunk_id


class EscalationDagTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_obj = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmp_obj.name)

    def tearDown(self) -> None:
        self.tmp_obj.cleanup()

    def test_balanced_clean_qa_skips_grammar_to_reviewer(self) -> None:
        orch = _build_orchestrator(self.tmp, "balanced")
        events: list[dict[str, Any]] = []
        orch.add_listener(events.append)
        try:
            chunk_id = _add_chunk(orch)
            orch._on_stage_done(
                "qa_validator",
                chunk_id,
                {"qa_checked": "Bonjour monde", "qa_issues": []},
            )
            reviewer_q = orch._workers.queues_for("reviewer").input
            grammar_q = orch._workers.queues_for("grammar_proofer").input
            self.assertEqual(reviewer_q.qsize(), 1)
            self.assertEqual(grammar_q.qsize(), 0)
            self.assertIn("dag_skip", [e.get("type") for e in events])
        finally:
            orch.store.close()

    def test_qa_issues_keep_grammar_proofer(self) -> None:
        orch = _build_orchestrator(self.tmp, "premium")
        events: list[dict[str, Any]] = []
        orch.add_listener(events.append)
        try:
            chunk_id = _add_chunk(orch)
            orch._on_stage_done(
                "qa_validator",
                chunk_id,
                {
                    "qa_checked": "Bonjour monde",
                    "qa_issues": [{"type": "missing", "message": "term"}],
                },
            )
            grammar_q = orch._workers.queues_for("grammar_proofer").input
            reviewer_q = orch._workers.queues_for("reviewer").input
            self.assertEqual(grammar_q.qsize(), 1)
            self.assertEqual(reviewer_q.qsize(), 0)
            self.assertNotIn("dag_skip", [e.get("type") for e in events])
        finally:
            orch.store.close()

    def test_premium_consistency_flags_escalate_to_terminology(self) -> None:
        orch = _build_orchestrator(self.tmp, "premium")
        events: list[dict[str, Any]] = []
        orch.add_listener(events.append)
        try:
            chunk_id = _add_chunk(orch)
            orch._on_stage_done(
                "consistency_checker",
                chunk_id,
                {
                    "glossary_applied": "Bonjour monde",
                    "consistency_flags": [{"term": "world", "seen": ["monde"]}],
                },
            )
            terminology_q = orch._workers.queues_for("terminology_researcher").input
            qa_q = orch._workers.queues_for("qa_validator").input
            self.assertEqual(terminology_q.qsize(), 1)
            self.assertEqual(qa_q.qsize(), 0)
            self.assertIn("dag_escalate", [e.get("type") for e in events])
        finally:
            orch.store.close()

    def test_balanced_consistency_flags_do_not_escalate(self) -> None:
        orch = _build_orchestrator(self.tmp, "balanced")
        events: list[dict[str, Any]] = []
        orch.add_listener(events.append)
        try:
            chunk_id = _add_chunk(orch)
            orch._on_stage_done(
                "consistency_checker",
                chunk_id,
                {
                    "glossary_applied": "Bonjour monde",
                    "consistency_flags": [{"term": "world", "seen": ["monde"]}],
                },
            )
            qa_q = orch._workers.queues_for("qa_validator").input
            terminology_q = orch._workers.queues_for("terminology_researcher").input
            self.assertEqual(qa_q.qsize(), 1)
            self.assertEqual(terminology_q.qsize(), 0)
            self.assertNotIn("dag_escalate", [e.get("type") for e in events])
        finally:
            orch.store.close()


if __name__ == "__main__":
    unittest.main()
