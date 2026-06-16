"""Test multi-source parser dispatch + schema accepts source_paths."""
import tempfile
import time
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from src.backend.server import create_app


class MultiSourceSchemaTest(unittest.TestCase):
    """POST /projects must accept source_paths (list) and source_path (str)."""

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

    def test_source_paths_list_accepted(self) -> None:
        files = [self.tmpdir / f"book_{i}.txt" for i in range(3)]
        for f in files:
            f.write_text(f"chapter 1 of {f.stem}\n\nchapter 2 of {f.stem}\n")

        body = {
            "project_dir": str(self.tmpdir / "out"),
            "source_paths": [str(f) for f in files],
            "source_lang": "en",
            "target_lang": "fr",
            "profile": "balanced",
            "output_format": "txt",
            "parse": False,
        }
        res = self.client.post("/projects", json=body)
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertEqual(len(data["source_paths"]), 3)
        self.assertTrue(all("book_" in p for p in data["source_paths"]))

    def test_source_path_string_accepted(self) -> None:
        """Legacy single-file payload still works."""
        f = self.tmpdir / "single.txt"
        f.write_text("hello\n")
        body = {
            "project_dir": str(self.tmpdir / "out"),
            "source_path": str(f),
            "source_lang": "en",
            "target_lang": "fr",
            "profile": "balanced",
            "output_format": "txt",
            "parse": False,
        }
        res = self.client.post("/projects", json=body)
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(len(res.json()["source_paths"]), 1)

    def test_empty_source_accepted_creates_empty_project(self) -> None:
        """Empty source_paths now creates an empty project (valid in
        the project-centric workflow — you add files later via Pipeline)."""
        project_dir = self.tmpdir / "out"
        body = {
            "name": "Empty Project",
            "project_dir": str(project_dir),
            "source_lang": "en",
            "target_lang": "fr",
            "profile": "balanced",
            "output_format": "txt",
            "parse": False,
        }
        res = self.client.post("/projects", json=body)
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertEqual(data["status"], "created")
        self.assertEqual(data["source_paths"], [])
        self.assertEqual(data["active_project_id"], data["project_id"])
        self.assertEqual(data["project"]["name"], "Empty Project")
        self.assertEqual(data["project"]["project_dir"], str(project_dir))
        self.assertTrue((project_dir / "source").is_dir())
        self.assertTrue((project_dir / "target").is_dir())
        self.assertTrue((project_dir / ".noveltrad").is_dir())

    def test_project_list_limit_and_newest_first(self) -> None:
        for idx in range(12):
            res = self.client.post(
                "/projects",
                json={
                    "name": f"Project {idx:02d}",
                    "project_dir": str(self.tmpdir / f"project_{idx:02d}"),
                    "parse": False,
                },
            )
            self.assertEqual(res.status_code, 200, res.text)
            time.sleep(0.002)

        res = self.client.get("/projects?limit=10")
        self.assertEqual(res.status_code, 200, res.text)
        projects = res.json()["projects"]
        self.assertEqual(len(projects), 10)
        self.assertEqual(projects[0]["name"], "Project 11")
        self.assertEqual(projects[-1]["name"], "Project 02")


class ParserMultiSourceTest(unittest.TestCase):
    """Parser should iterate source_paths and tag each chunk with source_file."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.tmpdir = Path(self._tmp.name)

    def tearDown(self) -> None:
        try:
            self._tmp.cleanup()
        except Exception:
            pass

    def test_parser_iterates_source_paths(self) -> None:
        from src.backend.agents.parser import Worker

        f1 = self.tmpdir / "a.txt"
        f1.write_text("First chapter.\n\nSecond chapter.\n")
        f2 = self.tmpdir / "b.txt"
        f2.write_text("Chapter alpha.\n\nChapter beta.\n")

        worker = Worker.__new__(Worker)
        captured: dict = {}

        def fake_emit_done_local(payload, terminal=False):
            captured["payload"] = payload
            captured["terminal"] = terminal
            return None

        worker._emit_done_local = fake_emit_done_local  # type: ignore[attr-defined]
        worker._emit_progress = lambda *a, **kw: None  # type: ignore[attr-defined]
        worker.stage = "parser"  # type: ignore[attr-defined]
        worker.worker_id = "parser__0"  # type: ignore[attr-defined]
        worker.identity = type(  # type: ignore[attr-defined]
            "I", (), {"worker_id": "parser__0"}
        )()

        msg = {
            "action": "parse",
            "payload": {
                "project_id": "proj_multi",
                "project_dir": str(self.tmpdir),
                "source_paths": [str(f1), str(f2)],
            },
        }
        result = worker.handle_task(msg)
        self.assertIsNone(result)
        self.assertTrue(captured["terminal"])
        payload = captured["payload"]
        # Both source paths are echoed back, regardless of how the
        # chunker groups paragraphs.
        self.assertEqual(payload["source_paths"], [str(f1), str(f2)])
        # Every chapter must carry a source_file stamp.
        chapters = payload["chapters"]
        self.assertGreaterEqual(len(chapters), 1)
        for chap in chapters:
            self.assertIn("source_file", chap)
            self.assertIn(chap["source_file"], [str(f1), str(f2)])
        # Both files must be represented.
        seen_sources = {chap["source_file"] for chap in chapters}
        self.assertEqual(seen_sources, {str(f1), str(f2)})


if __name__ == "__main__":
    unittest.main()
