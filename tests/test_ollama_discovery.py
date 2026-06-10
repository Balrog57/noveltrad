"""Tests for the Ollama auto-discovery layer.

Covers:
  * the ``discover_ollama_models`` helper in :mod:`llm_router.router`
  * the ``GET /llm/providers`` and ``POST /llm/providers/refresh`` REST
    endpoints exposed by :mod:`src.backend.server`.

The Ollama HTTP layer is replaced by an injectable opener so the
tests stay offline and fast.
"""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlsplit

from fastapi.testclient import TestClient

from src.backend.llm_router.router import (
    SUGGESTED_CLOUD_MODELS,
    SUGGESTED_OLLAMA_MODELS,
    OllamaModelInfo,
    discover_ollama_models,
)


# --- helpers ----------------------------------------------------------------


class _Resp:
    """Minimal urllib response stand-in. ``read()`` returns a fixed body."""

    def __init__(self, body: bytes, status: int = 200):
        self._buf = io.BytesIO(body)
        self.headers = {"Content-Length": str(len(body))}
        self.status = status

    def read(self, n: int = -1) -> bytes:
        if n < 0:
            return self._buf.read()
        return self._buf.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def _make_opener(responses: dict[str, _Resp]):
    """Return an ``opener(req, timeout)`` callable backed by a path→resp map.

    ``req`` may be a string URL or an object exposing ``.full_url``.
    """

    def _opener(req, timeout=None):  # type: ignore[no-untyped-def]
        url = req if isinstance(req, str) else getattr(req, "full_url", str(req))
        path = urlsplit(url).path
        if path not in responses:
            raise RuntimeError(f"unexpected path: {path}")
        return responses[path]

    return _opener


def _ollama_responses(models: list[dict] | None = None, version: str = "0.5.1") -> dict[str, _Resp]:
    if models is None:
        models = [
            {
                "name": "gemma3:4b",
                "size": 3_300_000_000,
                "modified_at": "2026-01-01T00:00:00Z",
                "details": {
                    "family": "gemma3",
                    "parameter_size": "4.3B",
                    "quantization_level": "Q4_0",
                },
            },
            {
                "name": "qwen2.5:7b",
                "size": 4_700_000_000,
                "modified_at": "2026-02-01T00:00:00Z",
                "details": {"family": "qwen2", "parameter_size": "7.6B", "quantization_level": "Q4_K_M"},
            },
        ]
    return {
        "/api/version": _Resp(json.dumps({"version": version}).encode("utf-8")),
        "/api/tags": _Resp(json.dumps({"models": models}).encode("utf-8")),
    }


# --- discover_ollama_models -------------------------------------------------


class DiscoverOllamaTests(unittest.TestCase):
    def test_unreachable_returns_error_and_empty_models(self):
        def _boom(req, timeout=None):
            raise ConnectionRefusedError("no ollama")

        info = discover_ollama_models("http://127.0.0.1:11434", opener=_boom)
        self.assertFalse(info["reachable"])
        self.assertIn("not reachable", info["error"])
        self.assertEqual(info["models"], [])

    def test_reachable_returns_models(self):
        info = discover_ollama_models(
            "http://127.0.0.1:11434", opener=_make_opener(_ollama_responses())
        )
        self.assertTrue(info["reachable"])
        self.assertEqual(info["version"], "0.5.1")
        self.assertIsNone(info["error"])
        self.assertEqual([m.name for m in info["models"]], ["gemma3:4b", "qwen2.5:7b"])
        first = info["models"][0]
        self.assertIsInstance(first, OllamaModelInfo)
        self.assertEqual(first.family, "gemma3")
        self.assertEqual(first.parameter_size, "4.3B")
        self.assertEqual(first.quantization, "Q4_0")
        self.assertGreater(first.size_bytes, 0)

    def test_strips_trailing_slash(self):
        seen_urls: list[str] = []

        def _opener(req, timeout=None):
            url = req if isinstance(req, str) else req.full_url
            seen_urls.append(url)
            return _Resp(json.dumps({"models": []}).encode("utf-8"))

        discover_ollama_models("http://127.0.0.1:11434/", opener=_opener)
        self.assertEqual(seen_urls[0], "http://127.0.0.1:11434/api/version")
        self.assertEqual(seen_urls[1], "http://127.0.0.1:11434/api/tags")

    def test_models_sorted_by_name(self):
        # unsorted input should be sorted in the output
        models = [
            {"name": "z-last"},
            {"name": "a-first"},
            {"name": "m-middle"},
        ]
        info = discover_ollama_models(
            "http://127.0.0.1:11434", opener=_make_opener(_ollama_responses(models))
        )
        self.assertEqual([m.name for m in info["models"]], ["a-first", "m-middle", "z-last"])

    def test_suggested_lists_are_non_empty(self):
        # Guard against accidental emptying of the curated lists.
        self.assertGreater(len(SUGGESTED_OLLAMA_MODELS), 0)
        self.assertGreater(len(SUGGESTED_CLOUD_MODELS), 0)
        for entry in SUGGESTED_OLLAMA_MODELS:
            self.assertIn("name", entry)
            self.assertIn("size", entry)
        for entry in SUGGESTED_CLOUD_MODELS:
            self.assertIn("name", entry)
            self.assertIn("provider", entry)
            self.assertIn("base_url", entry)

    def test_version_failure_does_not_break_tags(self):
        """If /api/version 404s but /api/tags works, we still return models."""

        def _opener(req, timeout=None):
            path = urlsplit(req if isinstance(req, str) else req.full_url).path
            if path == "/api/version":
                raise RuntimeError("no version endpoint")
            return _Resp(json.dumps({"models": [{"name": "x"}]}).encode("utf-8"))

        info = discover_ollama_models("http://127.0.0.1:11434", opener=_opener)
        # Version is best-effort, so an unreachable version endpoint is OK
        # as long as /api/tags is fine.
        self.assertTrue(info["reachable"])
        self.assertEqual([m.name for m in info["models"]], ["x"])


# --- /llm/providers REST endpoint ------------------------------------------


class LLMProvidersEndpointTests(unittest.TestCase):
    def setUp(self):
        # We need a real server instance with a temp DB and vector dir.
        from src.backend.server import create_app

        self._tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.app = create_app(
            db_path=Path(self._tmp.name) / "state.db",
            vector_dir=Path(self._tmp.name) / "vec",
        )
        self.client = TestClient(self.app)

    def tearDown(self):
        try:
            self.client.close()
        except Exception:
            pass
        # Drop the orchestrator / state store references to release the
        # SQLite file on Windows.
        import gc

        gc.collect()
        try:
            self._tmp.cleanup()
        except Exception:
            pass

    def test_get_providers_returns_shape_with_ollama_section(self):
        import src.backend.llm_router.router as rtr

        def _patched_urlopen(req, timeout=None):  # noqa: ARG001
            url = req if isinstance(req, str) else req.full_url
            return _make_opener(_ollama_responses())(url, timeout)

        original = rtr.urllib.request.urlopen
        rtr.urllib.request.urlopen = _patched_urlopen  # type: ignore[assignment]
        try:
            resp = self.client.get("/llm/providers")
        finally:
            rtr.urllib.request.urlopen = original  # type: ignore[assignment]
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("ollama", body)
        self.assertTrue(body["ollama"]["reachable"])
        self.assertEqual(body["ollama"]["version"], "0.5.1")
        names = [m["name"] for m in body["ollama"]["models"]]
        self.assertEqual(names, ["gemma3:4b", "qwen2.5:7b"])
        self.assertEqual(body["defaults"]["provider"], "ollama")
        self.assertGreater(len(body["ollama_suggestions"]), 0)
        self.assertGreater(len(body["cloud_suggestions"]), 0)

    def test_get_providers_unreachable(self):
        import src.backend.llm_router.router as rtr

        def _boom(req, timeout=None):  # noqa: ARG001
            raise ConnectionRefusedError("nope")

        original = rtr.urllib.request.urlopen
        rtr.urllib.request.urlopen = _boom  # type: ignore[assignment]
        try:
            resp = self.client.get("/llm/providers")
        finally:
            rtr.urllib.request.urlopen = original  # type: ignore[assignment]
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertFalse(body["ollama"]["reachable"])
        self.assertIn("not reachable", body["ollama"]["error"])
        # suggestions are still returned so the GUI has fallbacks.
        self.assertGreater(len(body["ollama_suggestions"]), 0)

    def test_refresh_returns_ok(self):
        resp = self.client.post("/llm/providers/refresh")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["ok"])
        self.assertIn("ollama", body)


if __name__ == "__main__":
    unittest.main()
