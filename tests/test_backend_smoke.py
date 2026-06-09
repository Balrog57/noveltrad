import os
import tempfile
import time
import unittest
from pathlib import Path


class BackendSmokeTests(unittest.TestCase):
    @unittest.skipUnless(
        os.environ.get("NOVELTRAD_RUN_SLOW_SMOKE") == "1",
        "set NOVELTRAD_RUN_SLOW_SMOKE=1 to run multiprocessing backend smoke",
    )
    def test_txt_pipeline_with_fake_providers(self):
        from fastapi.testclient import TestClient

        from src.backend.server import create_app

        old_env = dict(os.environ)
        os.environ["NOVELTRAD_TRANSLATION_TEST_MODE"] = "1"
        os.environ["NOVELTRAD_FAKE_LLM"] = "1"
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                source = root / "book.txt"
                source.write_text(
                    "Chapter 1\n\nThis is a short test paragraph for translation.",
                    encoding="utf-8",
                )
                app = create_app(db_path=root / ".state.db", vector_dir=root / ".vectors")
                with TestClient(app) as client:
                    res = client.post(
                        "/projects",
                        json={
                            "project_dir": str(root / "project"),
                            "source_path": str(source),
                            "source_lang": "en",
                            "target_lang": "fr",
                            "parse": True,
                        },
                    )
                    self.assertEqual(res.status_code, 200, res.text)
                    deadline = time.time() + 30
                    state = {}
                    while time.time() < deadline:
                        state = client.get("/pipeline/state").json()
                        artifact = state.get("output_artifact") or {}
                        if artifact.get("output_path"):
                            break
                        time.sleep(0.5)
                    artifact = state.get("output_artifact") or {}
                    self.assertTrue(artifact.get("output_path"), state)
                    self.assertTrue(Path(artifact["output_path"]).exists())
        finally:
            os.environ.clear()
            os.environ.update(old_env)


if __name__ == "__main__":
    unittest.main()
