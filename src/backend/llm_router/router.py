"""LiteLLM-style internal router for the v4 pipeline.

The router is the single gateway to LLM providers. All LLM-using
agents (LexiconBuilder, LLMPolisher, QAValidator's two-pass step)
call into this module instead of talking to OpenAI/Ollama directly.

Design points (from the plan §1, §3):
  * Two providers supported out of the box: Ollama (local) and any
    OpenAI-compatible cloud (OpenAI, OpenRouter, local llama.cpp
    server, vLLM, etc.).
  * Content-hash cache (SHA-512 over the JSON-serialised prompt +
    model + version). Persists to a JSON file under `cache_dir` so
    re-runs are free.
  * Serialized queue for Ollama: per the TBL lesson, parallel Ollama
    requests often OOM the GPU. The router exposes a configurable
    `parallel` count per provider.
  * Circuit breaker: if a provider fails 3 times in a row, it is
    marked `open` for 30s, and requests are routed to the next
    healthy provider.
  * Retry with exponential backoff: 3 attempts, 0.5s, 1s, 2s.

This module is GUI-free and PyQt6-free. The router can be used by
the FastAPI process and by the LLM-using agent subprocesses. If the
heavy `httpx` dependency is missing, we fall back to `urllib` so
the v4 minimal pipeline still works in environments without it.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import queue as _queue
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


# ---------- provider model ----------


@dataclass
class ProviderConfig:
    name: str
    kind: str  # "ollama" | "openai"
    base_url: str
    model: str
    api_key: str = ""
    parallel: int = 1
    timeout_s: float = 60.0
    options: dict[str, Any] = field(default_factory=dict)


# ---------- cache ----------


class ContentHashCache:
    """Persistent JSON cache keyed by SHA-512 of (prompt|model|version)."""

    def __init__(self, cache_dir: str | Path | None = None):
        self.cache_dir = (
            Path(cache_dir) if cache_dir else Path.home() / ".cache" / "noveltrad_llm"
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._path = self.cache_dir / "cache.json"
        self._lock = threading.Lock()
        self._data: dict[str, str] = self._load()

    def _load(self) -> dict[str, str]:
        if not self._path.exists():
            return {}
        try:
            with self._path.open("r", encoding="utf-8") as f:
                raw = json.load(f)
                return raw if isinstance(raw, dict) else {}
        except Exception:
            return {}

    def _save(self) -> None:
        try:
            with self._path.open("w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception:
            logger.warning("LLM cache: failed to persist to %s", self._path)

    @staticmethod
    def key(prompt: str, model: str, version: str = "v1") -> str:
        h = hashlib.sha512()
        h.update(model.encode("utf-8"))
        h.update(b"\0")
        h.update(version.encode("utf-8"))
        h.update(b"\0")
        h.update(prompt.encode("utf-8"))
        return h.hexdigest()

    def get(self, key: str) -> str | None:
        with self._lock:
            return self._data.get(key)

    def put(self, key: str, value: str) -> None:
        with self._lock:
            self._data[key] = value
            self._save()

    def clear(self) -> None:
        with self._lock:
            self._data.clear()
            self._save()


# ---------- circuit breaker ----------


@dataclass
class CircuitState:
    failures: int = 0
    opened_at: float = 0.0
    threshold: int = 3
    cooldown_s: float = 30.0

    def is_open(self) -> bool:
        if self.failures < self.threshold:
            return False
        return (time.time() - self.opened_at) < self.cooldown_s

    def record_success(self) -> None:
        self.failures = 0
        self.opened_at = 0.0

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.threshold and self.opened_at == 0.0:
            self.opened_at = time.time()


# ---------- router ----------


class LLMRouter:
    """Process-singleton LLM gateway."""

    def __init__(
        self,
        providers: list[ProviderConfig] | None = None,
        cache_dir: str | Path | None = None,
        version: str = "noveltrad-1.0",
    ):
        self.version = version
        self.providers: list[ProviderConfig] = list(providers or [])
        self.cache = ContentHashCache(cache_dir)
        self._circuits: dict[str, CircuitState] = {
            p.name: CircuitState() for p in self.providers
        }
        self._provider_locks: dict[str, threading.Semaphore] = {
            p.name: threading.Semaphore(max(1, p.parallel)) for p in self.providers
        }
        self._stats_lock = threading.Lock()
        self._stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "provider_calls": 0,
            "provider_failures": 0,
        }

    # ----- lifecycle -----

    def add_provider(self, p: ProviderConfig) -> None:
        self.providers.append(p)
        self._circuits[p.name] = CircuitState()
        self._provider_locks[p.name] = threading.Semaphore(max(1, p.parallel))

    def default_providers_from_env(self) -> None:
        """Populate the router from standard env vars (idempotent)."""
        ollama_base = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        ollama_model = os.environ.get("OLLAMA_MODEL", "gemma3:4b")
        if not any(p.kind == "ollama" for p in self.providers):
            self.add_provider(
                ProviderConfig(
                    name="ollama-default",
                    kind="ollama",
                    base_url=ollama_base,
                    model=ollama_model,
                    parallel=int(os.environ.get("OLLAMA_PARALLEL", "1")),
                )
            )
        cloud_key = os.environ.get("OPENAI_API_KEY", "")
        if cloud_key and not any(p.kind == "openai" for p in self.providers):
            self.add_provider(
                ProviderConfig(
                    name="openai-cloud",
                    kind="openai",
                    base_url=os.environ.get(
                        "OPENAI_BASE_URL", "https://api.openai.com/v1"
                    ),
                    model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
                    api_key=cloud_key,
                    parallel=int(os.environ.get("OPENAI_PARALLEL", "4")),
                )
            )

    # ----- public API -----

    def complete(
        self,
        prompt: str,
        *,
        model: str | None = None,
        use_cache: bool = True,
        max_retries: int = 3,
    ) -> str:
        """Return the completion text. May raise on hard failure."""
        if os.environ.get("NOVELTRAD_FAKE_LLM") in {"1", "true", "yes"}:
            return _fake_completion(prompt)
        provider = self._pick_provider(model)
        if provider is None:
            raise RuntimeError("No LLM providers configured")
        cache_key = self.cache.key(prompt, provider.model, self.version)
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                with self._stats_lock:
                    self._stats["cache_hits"] += 1
                return cached
        with self._stats_lock:
            self._stats["cache_misses"] += 1

        last_err: Exception | None = None
        for attempt in range(max_retries):
            try:
                text = self._call_provider_with_lock(provider, prompt)
                circuit = self._circuits[provider.name]
                circuit.record_success()
                self.cache.put(cache_key, text)
                with self._stats_lock:
                    self._stats["provider_calls"] += 1
                return text
            except Exception as exc:
                last_err = exc
                logger.warning(
                    "LLM call failed (provider=%s attempt=%d): %s",
                    provider.name,
                    attempt + 1,
                    exc,
                )
                self._circuits[provider.name].record_failure()
                with self._stats_lock:
                    self._stats["provider_failures"] += 1
                time.sleep(0.5 * (2**attempt))
        raise RuntimeError(
            f"LLM call failed after {max_retries} attempts: {last_err}"
        )

    def stats(self) -> dict[str, Any]:
        with self._stats_lock:
            return dict(self._stats)

    # ----- internals -----

    def _pick_provider(self, model: str | None) -> ProviderConfig | None:
        # Filter out providers with an open circuit.
        candidates = [
            p
            for p in self.providers
            if not self._circuits[p.name].is_open()
        ]
        if model:
            named = [p for p in candidates if p.model == model]
            if named:
                return named[0]
        if not candidates:
            candidates = self.providers  # all open, force one
        return candidates[0] if candidates else None

    def _call_provider_with_lock(
        self, provider: ProviderConfig, prompt: str
    ) -> str:
        sem = self._provider_locks[provider.name]
        sem.acquire()
        try:
            if provider.kind == "ollama":
                return _call_ollama(provider, prompt)
            if provider.kind == "openai":
                return _call_openai(provider, prompt)
            raise ValueError(f"Unknown provider kind: {provider.kind!r}")
        finally:
            sem.release()


# ---------- provider implementations ----------


def _call_ollama(p: ProviderConfig, prompt: str) -> str:
    url = p.base_url.rstrip("/") + "/api/generate"
    payload = {
        "model": p.model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2, **p.options},
    }
    raw = _http_post_json(url, payload, timeout=p.timeout_s)
    data = json.loads(raw)
    if "error" in data:
        raise RuntimeError(f"Ollama error: {data['error']}")
    return str(data.get("response", "")).strip()


def _call_openai(p: ProviderConfig, prompt: str) -> str:
    url = p.base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": p.model,
        "messages": [
            {"role": "system", "content": "You are a careful translator."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    raw = _http_post_json(
        url, payload, timeout=p.timeout_s, auth_header=f"Bearer {p.api_key}"
    )
    data = json.loads(raw)
    if "error" in data:
        raise RuntimeError(f"OpenAI error: {data['error']}")
    return str(data["choices"][0]["message"]["content"]).strip()


def _http_post_json(
    url: str, payload: dict[str, Any], timeout: float, auth_header: str = ""
) -> str:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST", headers={"Content-Type": "application/json"}
    )
    if auth_header:
        req.add_header("Authorization", auth_header)
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return resp.read().decode("utf-8", errors="replace")


def _fake_completion(prompt: str) -> str:
    """Deterministic local LLM used by smoke tests and offline demos."""
    lower = prompt.lower()
    if "strict json" in lower and '"terms"' in lower:
        return '{"terms": []}'
    if "strict json" in lower and '"issues"' in lower:
        return '{"issues": []}'
    if "strict json" in lower and '"suggestions"' in lower:
        return '{"reflection": "offline fake LLM", "suggestions": []}'
    marker = "CURRENT TRANSLATION:"
    if marker in prompt:
        return prompt.split(marker, 1)[1].strip()
    marker = "TEXT:"
    if marker in prompt:
        return prompt.split(marker, 1)[1].strip()
    return ""


# ---------- singleton ----------


_router: LLMRouter | None = None
_router_lock = threading.Lock()


def get_router() -> LLMRouter:
    global _router
    with _router_lock:
        if _router is None:
            _router = LLMRouter()
            _router.default_providers_from_env()
        return _router


__all__ = [
    "ProviderConfig",
    "ContentHashCache",
    "CircuitState",
    "LLMRouter",
    "get_router",
]
