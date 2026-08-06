"""LLM backend configuration.

CDC F2: hybrid support — local Ollama by default, optional OpenAI-compatible
remote provider (Groq, OpenRouter, DeepSeek) for machines without enough VRAM.

Privacy-first (CDC §5): local is the default and the only provider initialised
unless the user explicitly opts into a remote API key.
"""

from __future__ import annotations

from typing import Any

import requests
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_ollama import ChatOllama

# Remote provider imported lazily so a missing api key never breaks local use.
try:
    from langchain_openai import ChatOpenAI
    _HAS_OPENAI = True
except Exception:  # pragma: no cover - optional dependency
    _HAS_OPENAI = False


# Preset base URLs for common OpenAI-compatible providers (CDC F2.b).
REMOTE_PRESETS: dict[str, str] = {
    "groq": "https://api.groq.com/openai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "openai": "https://api.openai.com/v1",
    "lmstudio": "http://localhost:1234/v1",
}

_MODELS_TIMEOUT = 8  # seconds for the /api/tags probe


def list_ollama_models(host: str = "http://localhost:11434") -> list[str]:
    """List the models available on the local Ollama server (CDC Phase 1).

    Hits GET {host}/api/tags. Returns model names (e.g. ["qwen2.5:7b", ...]).
    Raises ConnectionError with a helpful message if the server is unreachable.
    """
    url = host.rstrip("/") + "/api/tags"
    try:
        resp = requests.get(url, timeout=_MODELS_TIMEOUT)
    except requests.RequestException as exc:
        raise ConnectionError(
            f"Impossible de joindre Ollama à {host}. "
            "Vérifiez qu'il tourne (ollama serve)."
        ) from exc
    if resp.status_code != 200:
        raise ConnectionError(f"Ollama /api/tags a renvoyé HTTP {resp.status_code}.")
    models = [m.get("name", "") for m in resp.json().get("models", [])]
    return [m for m in models if m]


def get_llm(
    *,
    provider: str = "ollama",
    model: str = "qwen2.5:7b",
    base_url: str | None = None,
    api_key: str | None = None,
    temperature: float = 0.3,
    **kwargs: Any,
) -> BaseChatModel:
    """Build a chat model for the requested provider.

    - provider="ollama"  -> local ChatOllama (default, privacy-first).
    - provider in REMOTE_PRESETS or any OpenAI-compatible id -> ChatOpenAI.

    For remote providers, ``base_url`` defaults to the known preset; ``api_key``
    is required (raise ValueError if missing).
    """
    if provider == "ollama":
        return ChatOllama(
            model=model,
            base_url=base_url or "http://localhost:11434",
            temperature=temperature,
            **kwargs,
        )

    if not _HAS_OPENAI:  # pragma: no cover
        raise RuntimeError(
            "Remote provider support requires langchain-openai. "
            "Install with: uv sync (it is a core dependency)."
        )

    if not api_key:
        raise ValueError(f"Remote provider '{provider}' requires an api_key.")

    resolved_base = base_url or REMOTE_PRESETS.get(provider)
    return ChatOpenAI(
        model=model,
        base_url=resolved_base,
        api_key=api_key,
        temperature=temperature,
        **kwargs,
    )
