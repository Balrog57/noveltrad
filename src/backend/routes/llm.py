"""LLM provider discovery endpoints (used by first-run wizard + settings)."""

from __future__ import annotations

import os
from typing import Any

from .deps import Deps


def register(app: Any, deps: Deps) -> None:
    @app.get("/llm/providers")
    def llm_providers(
        ollama_base_url: str = "http://127.0.0.1:11434",
    ) -> dict[str, Any]:
        """Discovery endpoint used by the first-run wizard and settings tab."""
        from src.backend.llm_router.router import (
            SUGGESTED_CLOUD_MODELS,
            SUGGESTED_OLLAMA_MODELS,
            discover_ollama_models,
            get_router,
        )

        discovery = discover_ollama_models(ollama_base_url)
        try:
            router = get_router()
            providers = [
                {
                    "name": p.name,
                    "kind": p.kind,
                    "base_url": p.base_url,
                    "model": p.model,
                }
                for p in router.providers
            ]
        except Exception as exc:
            providers = [{"error": str(exc)}]

        return {
            "ollama": {
                "reachable": bool(discovery.get("reachable")),
                "base_url": discovery.get("base_url"),
                "version": discovery.get("version"),
                "error": discovery.get("error"),
                "models": [
                    {
                        "name": m.name,
                        "size_bytes": m.size_bytes,
                        "family": m.family,
                        "parameter_size": m.parameter_size,
                        "quantization": m.quantization,
                        "modified_at": m.modified_at,
                    }
                    for m in (discovery.get("models") or [])
                ],
            },
            "ollama_suggestions": list(SUGGESTED_OLLAMA_MODELS),
            "cloud_suggestions": list(SUGGESTED_CLOUD_MODELS),
            "providers": providers,
            "defaults": {
                "provider": "ollama",
                "model": "gemma3:4b",
                "base_url": "http://127.0.0.1:11434",
            },
        }

    @app.post("/llm/providers/refresh")
    def llm_providers_refresh() -> dict[str, Any]:
        """Re-probe Ollama and rebuild the router providers from env."""
        from src.backend.llm_router.router import (
            SUGGESTED_CLOUD_MODELS,
            SUGGESTED_OLLAMA_MODELS,
            discover_ollama_models,
            get_router,
        )

        try:
            router = get_router()
            router.providers.clear()
            router._circuits.clear()  # type: ignore[attr-defined]
            router._provider_locks.clear()  # type: ignore[attr-defined]
            router.default_providers_from_env()
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

        base = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        discovery = discover_ollama_models(base)
        return {
            "ok": True,
            "ollama": {
                "reachable": bool(discovery.get("reachable")),
                "base_url": discovery.get("base_url"),
                "version": discovery.get("version"),
                "error": discovery.get("error"),
                "models": [
                    {"name": m.name, "size_bytes": m.size_bytes}
                    for m in (discovery.get("models") or [])
                ],
            },
            "ollama_suggestions": list(SUGGESTED_OLLAMA_MODELS),
            "cloud_suggestions": list(SUGGESTED_CLOUD_MODELS),
            "provider_count": len(router.providers),
        }


__all__ = ["register"]
