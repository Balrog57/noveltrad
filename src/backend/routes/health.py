"""Health and LLM diagnostics endpoints."""

from __future__ import annotations

import os
from typing import Any

from .deps import Deps


def register(app: Any, deps: Deps) -> None:
    @app.get("/health")
    def health() -> dict[str, Any]:
        from src.backend.engines.nllb_engine import diagnostics as nllb_diagnostics
        from src.backend.llm_router.router import get_router

        provider_count = 0
        try:
            router = get_router()
            provider_count = len(router.providers)
            llm_stats = router.stats()
            llm_ready = bool(router.providers) or os.environ.get("NOVELTRAD_FAKE_LLM") in {
                "1",
                "true",
                "yes",
            }
        except Exception as exc:
            llm_stats = {"error": str(exc)}
            llm_ready = False
        return {
            "ok": True,
            "version": _backend_version(),
            "vector_store": deps.store.vector_status,
            "nllb": nllb_diagnostics(),
            "llm": {
                "ready": llm_ready,
                "provider_count": provider_count,
                "stats": llm_stats,
                "mode": getattr(router, "mode", "offline") if llm_ready else "offline",
                "usage": router.usage() if llm_ready else {},
            },
        }

    @app.get("/usage")
    def usage() -> dict[str, Any]:
        from src.backend.llm_router.router import get_router

        try:
            router = get_router()
            return {
                "mode": router.mode,
                **router.usage(),
            }
        except Exception as exc:
            return {"mode": "offline", "error": str(exc)}


def _backend_version() -> str:
    from src.backend import __version__

    return __version__


__all__ = ["register"]
