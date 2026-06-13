"""Headless client example for the NovelTrad v4 backend.

This script shows the canonical API flow without the GUI:

    1. Health-check the backend.
    2. Create a project (parse=true triggers the parser agent).
    3. Poll /pipeline/state until the output_artifact appears.
    4. Download / open the resulting file.

Run the backend first:

    python -m src.backend.server --host 127.0.0.1 --port 8765

Then run this script:

    python examples/headless_client.py path/to/source.txt

The script exits non-zero if the pipeline does not complete within
the deadline or if the backend reports regressions.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


BASE_URL = "http://127.0.0.1:8765"


def _request(method: str, path: str, body: dict[str, Any] | None = None, timeout: float = 30.0) -> Any:
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        raw = resp.read().decode("utf-8", errors="replace")
        if not raw:
            return None
        return json.loads(raw)


def _health() -> dict[str, Any]:
    return _request("GET", "/health", timeout=5.0) or {}


def wait_for_backend(timeout_s: float = 30.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            if _health().get("ok"):
                return
        except urllib.error.URLError:
            pass
        time.sleep(0.5)
    raise RuntimeError("Backend did not become ready in time")


def create_project(source_path: Path, target_dir: Path, profile: str, fmt: str) -> str:
    project_id = source_path.stem[:12]
    output_path = target_dir / f"{source_path.stem}_{profile}.{fmt}"
    req = {
        "project_id": project_id,
        "project_dir": str(target_dir),
        "source_path": str(source_path),
        "source_lang": "auto",
        "target_lang": "fr",
        "output_path": str(output_path),
        "output_format": fmt,
        "profile": profile,
        "parse": True,
    }
    res = _request("POST", "/projects", body=req)
    if not isinstance(res, dict) or res.get("status") != "created":
        raise RuntimeError(f"Project creation failed: {res}")
    return project_id


def wait_for_output(project_id: str, deadline_s: float = 120.0) -> dict[str, Any]:
    deadline = time.time() + deadline_s
    while time.time() < deadline:
        state = _request("GET", "/pipeline/state", timeout=5.0) or {}
        artifact = state.get("output_artifact") or {}
        if artifact.get("output_path"):
            return artifact
        pending = state.get("pending_hltl", 0)
        if pending > 0:
            print(f"[{project_id}] {pending} HITL request(s) pending — manual intervention required")
        time.sleep(1.0)
    raise RuntimeError("Pipeline did not produce an output artifact in time")


def main(argv: list[str] | None = None) -> int:
    global BASE_URL
    parser = argparse.ArgumentParser(description="NovelTrad headless client")
    parser.add_argument("source", type=Path, help="Source file to translate")
    parser.add_argument("--profile", default="balanced", choices=["eco", "balanced", "premium"])
    parser.add_argument("--format", default="txt", choices=["txt", "epub", "epub_bilingual", "docx", "srt"])
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args(argv)

    BASE_URL = args.base_url.rstrip("/")

    source = Path(args.source).expanduser().resolve()
