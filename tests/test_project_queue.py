"""Test project queue: second start() while busy should queue, not raise.

These tests bypass the HTTP layer and exercise the orchestrator's
``start()`` method directly so they don't have to spawn workers.
"""
import tempfile
import threading
import time
import unittest
from pathlib import Path

from src.backend.orchestrator.orchestrator import Orchestrator, ProjectContext
from src.backend.orchestrator.state_store import StateStore


def _ctx(pid: str, src: str, project_dir: Path) -> ProjectContext:
    return ProjectContext(
        project_id=pid,
        project_dir=project_dir,
        source_path=Path(src),
        source_paths=[Path(src)],
        source_lang="en",
        target_lang="fr",
        profile="balanced",
        output_format="txt",
    )


class ProjectQueueTest(unittest.TestCase):
    """When the pipeline is busy, ``start`` enqueues instead of raising."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.tmpdir = Path(self._tmp.name)
        self.store = StateStore(str(self.tmpdir / "state.db"))
        self.orch = Orchestrator(self.store)

    def tearDown(self) -> None:
        try:
            self.orch.shutdown()
        except Exception:
            pass
        try:
            self._tmp.cleanup()
        except Exception:
            pass

    def test_second_start_queues_instead_of_raising(self) -> None:
        f1 = self.tmpdir / "a.txt"
        f1.write_text("first\n")
        f2 = self.tmpdir / "b.txt"
        f2.write_text("second\n")

        # First project starts; status becomes "running"
        p1 = _ctx("p1", str(f1), self.tmpdir / "p1")
        self.orch.start(p1)
        self.assertEqual(self.orch._project.project_id, "p1")

        # Second project would normally raise RuntimeError; with the
        # queue it should be appended to the FIFO.
        p2 = _ctx("p2", str(f2), self.tmpdir / "p2")
        self.orch.start(p2)  # must NOT raise
        self.assertEqual(len(self.orch._project_queue), 1)
        self.assertEqual(self.orch._project_queue[0].project_id, "p2")

    def test_third_call_keeps_running_project_intact(self) -> None:
        f1 = self.tmpdir / "a.txt"; f1.write_text("a\n")
        f2 = self.tmpdir / "b.txt"; f2.write_text("b\n")
        f3 = self.tmpdir / "c.txt"; f3.write_text("c\n")
        self.orch.start(_ctx("p1", str(f1), self.tmpdir / "p1"))
        self.orch.start(_ctx("p2", str(f2), self.tmpdir / "p2"))
        self.orch.start(_ctx("p3", str(f3), self.tmpdir / "p3"))
        # p1 still running, p2 + p3 in queue
        self.assertEqual(self.orch._project.project_id, "p1")
        self.assertEqual(
            [q.project_id for q in self.orch._project_queue],
            ["p2", "p3"],
        )

    def test_snapshot_exposes_queue(self) -> None:
        f1 = self.tmpdir / "a.txt"; f1.write_text("a\n")
        f2 = self.tmpdir / "b.txt"; f2.write_text("b\n")
        self.orch.start(_ctx("p1", str(f1), self.tmpdir / "p1"))
        self.orch.start(_ctx("p2", str(f2), self.tmpdir / "p2"))
        snap = self.orch.snapshot()
        self.assertEqual(snap["project"]["project_id"], "p1")
        self.assertEqual(snap["project"]["source_path"], str(f1))
        self.assertEqual(snap["project"]["source_paths"], [str(f1)])
        self.assertEqual(snap["project"]["profile"], "balanced")
        self.assertEqual(snap["project"]["output_format"], "txt")
        self.assertEqual(snap["project_queue_size"], 1)
        self.assertEqual(snap["project_queue"][0]["project_id"], "p2")
        self.assertEqual(snap["project_queue"][0]["source_paths"], [str(f2)])

    def test_stop_clears_queue(self) -> None:
        f1 = self.tmpdir / "a.txt"; f1.write_text("a\n")
        f2 = self.tmpdir / "b.txt"; f2.write_text("b\n")
        f3 = self.tmpdir / "c.txt"; f3.write_text("c\n")
        self.orch.start(_ctx("p1", str(f1), self.tmpdir / "p1"))
        self.orch.start(_ctx("p2", str(f2), self.tmpdir / "p2"))
        self.orch.start(_ctx("p3", str(f3), self.tmpdir / "p3"))
        self.orch.stop()
        self.assertEqual(len(self.orch._project_queue), 0)


if __name__ == "__main__":
    unittest.main()
