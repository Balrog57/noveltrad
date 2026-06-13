"""Tests that the backend exposes a consistent, expected version."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import src
from src.backend import __version__ as backend_version
from src.backend.server import create_app


class HealthVersionTests(unittest.TestCase):
    def test_top_level_and_backend_versions_match(self) -> None:
        self.assertEqual(src.__version__, backend_version)

    def test_pyproject_version_matches_code(self) -> None:
        project_root = Path(__file__).resolve().parent.parent
        pyproject = project_root / "pyproject.toml"
        self.assertTrue(pyproject.exists(), "pyproject.toml must exist")
        version_line = next(
            (line for line in pyproject.read_text(encoding="utf-8").splitlines() if line.startswith("version")),
            None,
        )
        self.assertIsNotNone(version_line, "pyproject.toml must declare a version")
        toml_version = version_line.split("=", 1)[1].strip().strip('"')
        self.assertEqual(toml_version, src.__version__)

    def test_health_endpoint_returns_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            app = create_app(db_path=root / "state.db", vector_dir=root / "vectors")
            with TestClient(app) as client:
                res = client.get("/health")
                self.assertEqual(res.status_code, 200)
                body = res.json()
                self.assertTrue(body.get("ok"))
                self.assertEqual(body.get("version"), "4.1.0")


if __name__ == "__main__":
    unittest.main()
