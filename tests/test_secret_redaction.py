import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from src.backend.server import create_app


class SecretRedactionTests(unittest.TestCase):
    def test_llm_provider_diagnostics_do_not_expose_api_key(self) -> None:
        old = os.environ.get("OPENAI_API_KEY")
        os.environ["OPENAI_API_KEY"] = "sk-secret-for-test"
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                app = create_app(
                    db_path=root / "state.db",
                    vector_dir=root / "vectors",
                )
                with TestClient(app) as client:
                    body = client.get("/llm/providers").json()
            self.assertNotIn("sk-secret-for-test", repr(body))
            self.assertNotIn("api_key", repr(body).lower())
        finally:
            if old is None:
                os.environ.pop("OPENAI_API_KEY", None)
            else:
                os.environ["OPENAI_API_KEY"] = old


if __name__ == "__main__":
    unittest.main()
