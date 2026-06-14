"""Test DELETE /projects/{pid}/queue (remove queued project)."""
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from src.backend.server import create_app


class RemoveQueuedProjectTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.tmpdir = Path(self._tmp.name)
        self.app = create_app(db_path=str(self.tmpdir / "state.db"))
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        try:
            self._tmp.cleanup()
        except Exception:
            pass

    def test_remove_queued_project_via_orchestrator(self) -> None:
        from src.backend.orchestrator.orchestrator import (
            Orchestrator,
            ProjectContext,
        )
        from src.backend.orchestrator.state_store import StateStore

        store = StateStore(str(self.tmpdir / "s2.db"))
        orch = Orchestrator(store)
        try:
            f1 = self.tmpdir / "a.txt"; f1.write_text("a\n")
            f2 = self.tmpdir / "b.txt"; f2.write_text("b\n")
            f3 = self.tmpdir / "c.txt"; f3.write_text("c\n")
            orch.start(
                ProjectContext(
                    project_id="p1",
                    project_dir=self.tmpdir,
                    source_path=f1,
                    source_paths=[f1],
                    source_lang="en",
                    target_lang="fr",
                )
            )
            orch.start(
                ProjectContext(
                    project_id="p2",
                    project_dir=self.tmpdir,
                    source_path=f2,
                    source_paths=[f2],
                    source_lang="en",
                    target_lang="fr",
                )
            )
            orch.start(
                ProjectContext(
                    project_id="p3",
                    project_dir=self.tmpdir,
                    source_path=f3,
                    source_paths=[f3],
                    source_lang="en",
                    target_lang="fr",
                )
            )
            self.assertEqual([p.project_id for p in orch._project_queue], ["p2", "p3"])
            self.assertTrue(orch.remove_queued_project("p2"))
            self.assertEqual([p.project_id for p in orch._project_queue], ["p3"])
            # Second call returns False (already removed)
            self.assertFalse(orch.remove_queued_project("p2"))
            # Cannot remove the running project
            self.assertFalse(orch.remove_queued_project("p1"))
        finally:
            orch.shutdown()

    def test_remove_queued_route(self) -> None:
        # Fake a project on the orchestrator. We need to reach the
        # orchestrator instance from the app; create_app() returns a
        # FastAPI app with a single Orchestrator wired up by the
        # server factory. We poke it directly through the dependency.
        from src.backend.server import create_app
        # Build a fresh app with the dependency we can inspect
        app = create_app(db_path=str(self.tmpdir / "s3.db"))
        client = TestClient(app)
        # We can call the route even with no project to verify the
        # 404 response shape.
        res = client.delete("/projects/does-not-exist/queue")
        self.assertEqual(res.status_code, 404)


if __name__ == "__main__":
    unittest.main()
