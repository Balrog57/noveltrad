import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from src.backend.server import create_app


class ProjectLocalDataTests(unittest.TestCase):
    def test_clear_project_local_data_removes_only_project_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_dir = root / "project"
            project_dir.mkdir()
            vectors = project_dir / ".noveltrad_vectors"
            vectors.mkdir()
            cache = project_dir / ".llm_cache"
            cache.mkdir()
            (cache / "entry.json").write_text("{}", encoding="utf-8")
            outside = root / "outside.txt"
            outside.write_text("keep", encoding="utf-8")
            source = root / "source.txt"
            source.write_text("Chapter 1\n\nHello.", encoding="utf-8")

            app = create_app(db_path=root / "state.db", vector_dir=root / "vectors")
            with TestClient(app) as client:
                created = client.post(
                    "/projects",
                    json={
                        "project_id": "p-local",
                        "project_dir": str(project_dir),
                        "source_path": str(source),
                        "source_lang": "en",
                        "target_lang": "fr",
                        "parse": False,
                    },
                )
                self.assertEqual(created.status_code, 200, created.text)

                resp = client.delete("/projects/p-local/local-data")
                self.assertEqual(resp.status_code, 200, resp.text)
                body = resp.json()
                self.assertTrue(body["ok"])
                self.assertIn("sqlite:project_metadata", body["removed"])
                self.assertFalse(vectors.exists())
                self.assertFalse(cache.exists())
                self.assertTrue(outside.exists())

                projects = client.get("/projects").json()["projects"]
                self.assertEqual(projects, [])

    def test_clear_project_local_data_rejects_unknown_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            app = create_app(db_path=root / "state.db", vector_dir=root / "vectors")
            with TestClient(app) as client:
                resp = client.delete("/projects/missing/local-data")
                self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
