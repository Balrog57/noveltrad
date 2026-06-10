"""GUI helpers around the LLM discovery REST endpoint.

This module is GUI-only (PyQt6). It wraps ``GET /llm/providers`` and
``POST /llm/providers/refresh`` so the FirstRunWizard and the
Settings tab share the same auto-detection logic.

The helpers are deliberately tolerant: when the backend is not
running yet (cold start, the wizard runs before the FastAPI
process), we fall back to a static discovery call against
``http://127.0.0.1:11434`` so the user still gets a model picker.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class ProviderChoice:
    """One selectable model in the discovery panel."""

    label: str
    model: str
    provider_kind: str  # "ollama" or "openai"
    base_url: str = ""
    notes: str = ""
    installed: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    def display(self) -> str:
        tag = "  (installed)" if self.installed else ""
        if self.notes:
            return f"{self.label}{tag}  — {self.notes}"
        return f"{self.label}{tag}"


def _http_get_json(url: str, timeout: float = 3.0) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "NovelTrad-GUI/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def _http_post_json(url: str, timeout: float = 5.0) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=b"",
        method="POST",
        headers={"Accept": "application/json", "User-Agent": "NovelTrad-GUI/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def fetch_provider_choices(
    backend_url: str = "http://127.0.0.1:8765",
    *,
    opener: Optional[Callable[[str, float], object]] = None,
) -> dict[str, Any]:
    """Call the backend's discovery endpoint and bucket the choices.

    Returns a dict with three lists:
      * ``ollama_choices``: installed local models (each has
        ``installed=True``).
      * ``ollama_suggestions``: curated models the user can paste
        into Ollama (gemma3:4b, llama3.1:8b, ...). None of them are
        flagged as installed.
      * ``cloud_choices``: curated OpenAI-compatible endpoints.

    The function never raises; on failure the buckets are returned
    empty and ``error`` is set. The caller can then show a static
    default or hide the picker.
    """
    out: dict[str, Any] = {
        "ollama_choices": [],
        "ollama_suggestions": [],
        "cloud_choices": [],
        "ollama": {
            "reachable": False,
            "version": None,
            "error": None,
        },
        "error": None,
    }
    url = backend_url.rstrip("/") + "/llm/providers"
    try:
        if opener is not None:
            with opener(url, 5.0) as resp:  # type: ignore[attr-defined]
                payload = json.loads(resp.read().decode("utf-8", errors="replace"))
        else:
            payload = _http_get_json(url, timeout=5.0)
    except Exception as exc:  # noqa: BLE001
        out["error"] = f"discovery endpoint unreachable: {exc}"
        return out

    ollama = payload.get("ollama") or {}
    out["ollama"] = {
        "reachable": bool(ollama.get("reachable")),
        "version": ollama.get("version"),
        "error": ollama.get("error"),
    }

    for m in ollama.get("models") or []:
        name = str(m.get("name") or "").strip()
        if not name:
            continue
        size = m.get("size_bytes") or 0
        size_gb = round(int(size) / (1024**3), 1) if size else None
        notes_bits = []
        if m.get("parameter_size"):
            notes_bits.append(str(m["parameter_size"]))
        if m.get("quantization"):
            notes_bits.append(str(m["quantization"]))
        if size_gb:
            notes_bits.append(f"{size_gb} GB")
        out["ollama_choices"].append(
            ProviderChoice(
                label=name,
                model=name,
                provider_kind="ollama",
                base_url=str(ollama.get("base_url") or "http://127.0.0.1:11434"),
                notes=", ".join(notes_bits),
                installed=True,
                extra={"size_bytes": size},
            )
        )

    for s in payload.get("ollama_suggestions") or []:
        out["ollama_suggestions"].append(
            ProviderChoice(
                label=str(s.get("name") or ""),
                model=str(s.get("name") or ""),
                provider_kind="ollama",
                base_url=str(ollama.get("base_url") or "http://127.0.0.1:11434"),
                notes=f"{s.get('size', '')} — {s.get('notes', '')}".strip(" —"),
                installed=False,
            )
        )

    for s in payload.get("cloud_suggestions") or []:
        out["cloud_choices"].append(
            ProviderChoice(
                label=str(s.get("name") or ""),
                model=str(s.get("name") or ""),
                provider_kind="openai",
                base_url=str(s.get("base_url") or ""),
                notes=f"{s.get('provider', '')} — {s.get('notes', '')}".strip(" —"),
                installed=False,
            )
        )

    return out


def refresh_router(backend_url: str = "http://127.0.0.1:8765") -> dict[str, Any]:
    """Call ``POST /llm/providers/refresh`` so the backend re-reads env."""
    url = backend_url.rstrip("/") + "/llm/providers/refresh"
    try:
        return _http_post_json(url, timeout=8.0)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


__all__ = [
    "ProviderChoice",
    "fetch_provider_choices",
    "refresh_router",
]
