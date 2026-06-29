"""Shared HTTP client + config helpers for the CLI.

Before the v4 split these lived at the top of ``src/backend/cli.py``
alongside the 800-line argparse tree. They are now in their own module
so the per-subcommand modules in :mod:`src.backend.cli_commands` can
share them without dragging in the argparse tree.

What lives here
---------------
* ``load_config``             -- apply user config to env vars.
* ``make_client``             -- build a FastAPI TestClient for embedded mode.
* ``RemoteClient`` / ``RemoteResponse`` -- thin ``requests`` wrapper that
  mirrors TestClient's API so the subcommands are mode-agnostic.
* ``get_client``              -- pick TestClient vs RemoteClient based on ``--remote``.
* ``base_url`` + ``api_get`` / ``api_post`` / ``api_delete`` -- low-level
  ``requests`` shortcuts for the subcommands that just want a single
  HTTP call.

Everything in this module is internal to the CLI. Nothing in
``src/backend/`` outside of ``cli.py`` and ``cli_commands/`` should
import from here.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any


# ── Config loading ───────────────────────────────────────────────────────


def load_config(verbose: bool = False) -> None:
    """Apply user config to env vars (NLLB_MODEL, OLLAMA_MODEL, etc.)."""
    try:
        from src.gui.app_config import ConfigManager

        ConfigManager().apply_environment()
        if verbose:
            print(
                f"[cli] Config loaded: NLLB={os.environ.get('NLLB_MODEL', '?')}, "
                f"LLM={os.environ.get('OLLAMA_MODEL', '?')}"
            )
    except Exception as e:
        if verbose:
            print(f"[cli] Config skipped: {e}")


# ── Embedded TestClient ─────────────────────────────────────────────────


def make_client():
    """Return a FastAPI TestClient with config loaded."""
    from fastapi.testclient import TestClient

    from src.backend.server import create_app

    tmp = tempfile.mkdtemp(prefix="noveltrad_cli_")
    app = create_app(
        db_path=Path(tmp) / ".state.db", vector_dir=Path(tmp) / ".vectors"
    )
    return TestClient(app)


# ── Remote client (mirrors TestClient API) ──────────────────────────────


class RemoteClient:
    """Thin wrapper around ``requests`` that mirrors TestClient's API.

    The subcommands do ``client.get(path).json()`` /
    ``client.post(path, json=payload)`` etc. To keep them mode-agnostic
    we wrap the remote HTTP client in the same shape.
    """

    def __init__(self, base_url: str):
        import requests as _requests

        self._r = _requests
        self._base = base_url.rstrip("/")

    def get(self, path: str, **kw):
        return RemoteResponse(self._r.get(f"{self._base}{path}", timeout=30, **kw))

    def post(self, path: str, **kw):
        json_data = kw.pop("json", kw.pop("data", None))
        return RemoteResponse(
            self._r.post(f"{self._base}{path}", json=json_data, timeout=60, **kw)
        )

    def put(self, path: str, **kw):
        json_data = kw.pop("json", kw.pop("data", None))
        return RemoteResponse(
            self._r.put(f"{self._base}{path}", json=json_data, timeout=30, **kw)
        )

    def delete(self, path: str, **kw):
        return RemoteResponse(
            self._r.delete(f"{self._base}{path}", timeout=30, **kw)
        )


class RemoteResponse:
    def __init__(self, resp: Any) -> None:
        self.status_code = resp.status_code
        self._resp = resp

    def json(self):
        return self._resp.json()

    @property
    def text(self) -> str:
        return self._resp.text


def get_client(args) -> Any:
    """Return a TestClient (embedded) or RemoteClient (``--remote``)."""
    if getattr(args, "remote", False):
        base = f"http://{os.environ.get('NOVELTRAD_HOST', '127.0.0.1')}:{os.environ.get('NOVELTRAD_PORT', '8765')}"
        return RemoteClient(base)
    return make_client()


# ── Low-level shortcuts (used by subcommands that want a single call) ──


def base_url() -> str:
    return f"http://{os.environ.get('NOVELTRAD_HOST', '127.0.0.1')}:{os.environ.get('NOVELTRAD_PORT', '8765')}"


def api_get(path: str):
    import requests

    r = requests.get(f"{base_url()}{path}", timeout=10)
    r.raise_for_status()
    return r.json()


def api_post(path: str, data: dict | None = None):
    import requests

    r = requests.post(f"{base_url()}{path}", json=data or {}, timeout=30)
    r.raise_for_status()
    return r.json()


def api_delete(path: str):
    import requests

    r = requests.delete(f"{base_url()}{path}", timeout=10)
    r.raise_for_status()
    return r.json()
