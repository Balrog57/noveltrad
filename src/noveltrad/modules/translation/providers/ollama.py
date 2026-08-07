"""Ollama adapter (SDD 14.14): /api/tags and /api/chat with stream=false."""

from __future__ import annotations

import httpx

from noveltrad.core.contracts import (
    CompletionRequest,
    CompletionResponse,
    FinishReason,
    PipelineSnapshot,
    ValidationReport,
)
from noveltrad.core.exceptions import ProviderError

from .base import build_client


class OllamaProvider:
    def __init__(
        self, client: httpx.AsyncClient | None = None, base_url: str | None = None
    ) -> None:
        self._client = client or build_client()
        self._owns_client = client is None
        self._base_url_value = base_url or "http://localhost:11434"

    async def validate_configuration(self, snapshot: PipelineSnapshot) -> ValidationReport:
        self._base_url_value = snapshot.base_url
        try:
            response = await self._client.get(f"{self._base_url_value}/api/tags")
        except httpx.HTTPError as exc:
            return ValidationReport(
                False, ("PROVIDER_UNREACHABLE",), (f"provider unreachable: {exc}",)
            )
        if response.status_code != 200:
            return ValidationReport(
                False,
                ("PROVIDER_ERROR",),
                (f"provider error: HTTP {response.status_code}",),
            )
        models = [m.get("name") for m in response.json().get("models", [])]
        if snapshot.model not in models:
            return ValidationReport(
                False,
                ("MODEL_NOT_FOUND",),
                (f"model {snapshot.model} not installed",),
            )
        return ValidationReport(True, (), ())

    async def list_models(self) -> tuple[str, ...]:
        try:
            response = await self._client.get(f"{self._base_url_value}/api/tags")
        except httpx.HTTPError as exc:
            raise ProviderError("PROVIDER_UNREACHABLE", False) from exc
        if response.status_code != 200:
            raise ProviderError("LIST_MODELS_FAILED", False)
        return tuple(m.get("name") for m in response.json().get("models", []))

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        payload = {
            "model": request.model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.payload_json},
            ],
            "stream": False,
            "temperature": request.temperature,
            "options": {},
        }
        if request.max_output_tokens:
            payload["options"]["num_predict"] = request.max_output_tokens
        try:
            response = await self._client.post(f"{self._base_url_value}/api/chat", json=payload)
        except httpx.HTTPError as exc:
            raise ProviderError("NETWORK_ERROR", True) from exc
        if response.status_code != 200:
            code = "RATE_LIMITED" if response.status_code == 429 else "PROVIDER_ERROR"
            retry_after = response.headers.get("Retry-After")
            from ..retry import parse_retry_after

            return (
                CompletionResponse(
                    text="",
                    finish_reason=FinishReason.OTHER,
                    input_tokens=None,
                    output_tokens=None,
                    retry_after_seconds=parse_retry_after(retry_after),
                    provider_request_id=None,
                )
                if response.status_code in (429, 500, 502, 503, 504)
                else _raise(code, response)
            )
        data = response.json()
        message = data.get("message", {})
        text = message.get("content", "")
        done_reason = data.get("done_reason")
        finish = FinishReason.STOP if done_reason == "stop" else FinishReason.OTHER
        return CompletionResponse(
            text=text,
            finish_reason=finish,
            input_tokens=data.get("prompt_eval_count"),
            output_tokens=data.get("eval_count"),
            retry_after_seconds=None,
            provider_request_id=None,
        )

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()


def _raise(code: str, response: httpx.Response) -> CompletionResponse:
    raise ProviderError(code, False, safe_message=f"provider error: HTTP {response.status_code}")
