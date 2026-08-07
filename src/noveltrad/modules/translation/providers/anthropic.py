"""Anthropic adapter (Claude): native Messages API.

Endpoint: POST {base_url}/v1/messages with x-api-key and
anthropic-version: 2023-06-01. The response returns content blocks with
text plus stop_reason and usage counters.
"""

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

_ANTHROPIC_VERSION = "2023-06-01"


class AnthropicProvider:
    def __init__(
        self, client: httpx.AsyncClient | None = None, base_url: str | None = None
    ) -> None:
        self._client = client or build_client()
        self._owns_client = client is None
        self._base = (base_url or "https://api.anthropic.com").rstrip("/")
        self._api_key: str | None = None

    def set_base_url(self, base_url: str) -> None:
        self._base = base_url.rstrip("/")

    def set_api_key(self, api_key: str | None) -> None:
        self._api_key = api_key

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self._api_key or "",
            "anthropic-version": _ANTHROPIC_VERSION,
        }
        return headers

    async def validate_configuration(self, snapshot: PipelineSnapshot) -> ValidationReport:
        if not self._api_key:
            return ValidationReport(
                False, ("API_KEY_MISSING",), ("API key required for Anthropic",)
            )
        # minimal completion to prove model access
        request = CompletionRequest(
            request_id="validate",
            segment_id=0,
            stage=snapshot.provider.value,  # type: ignore[arg-type]
            system_prompt="Reply with exactly: OK",
            payload_json='{"ping": 1}',
            model=snapshot.model,
            temperature=0.0,
            max_output_tokens=8,
        )
        try:
            await self.complete(request)
        except ProviderError as exc:
            return ValidationReport(False, (exc.error_code,), (exc.safe_message or exc.error_code,))
        return ValidationReport(True, (), ())

    async def list_models(self) -> tuple[str, ...]:
        # Anthropic has no public /models endpoint; fall back to known models.
        return _KNOWN_MODELS

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        payload = {
            "model": request.model,
            "system": request.system_prompt,
            "messages": [{"role": "user", "content": request.payload_json}],
            "max_tokens": request.max_output_tokens,
            "temperature": request.temperature,
        }
        try:
            response = await self._client.post(
                f"{self._base}/v1/messages", json=payload, headers=self._headers()
            )
        except httpx.HTTPError as exc:
            raise ProviderError("NETWORK_ERROR", True) from exc
        if response.status_code != 200:
            if response.status_code in (429, 500, 502, 503, 504):
                from ..retry import parse_retry_after

                return CompletionResponse(
                    text="",
                    finish_reason=FinishReason.OTHER,
                    input_tokens=None,
                    output_tokens=None,
                    retry_after_seconds=parse_retry_after(response.headers.get("retry-after")),
                    provider_request_id=None,
                )
            if response.status_code in (401, 403):
                raise ProviderError("AUTH_FAILED", False)
            raise ProviderError(
                "PROVIDER_ERROR", False, safe_message=f"provider error: HTTP {response.status_code}"
            )
        data = response.json()
        blocks = data.get("content", [])
        text = "".join(block.get("text", "") for block in blocks if block.get("type") == "text")
        stop_reason = data.get("stop_reason")
        finish = FinishReason.STOP if stop_reason == "end_turn" else FinishReason.OTHER
        usage = data.get("usage", {})
        return CompletionResponse(
            text=text,
            finish_reason=finish,
            input_tokens=usage.get("input_tokens"),
            output_tokens=usage.get("output_tokens"),
            retry_after_seconds=None,
            provider_request_id=data.get("id"),
        )

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()


_KNOWN_MODELS: tuple[str, ...] = (
    "claude-opus-4-20250514",
    "claude-sonnet-4-20250514",
    "claude-3-7-sonnet-20250219",
    "claude-3-5-sonnet-20241022",
    "claude-3-5-haiku-20241022",
    "claude-3-opus-20240229",
    "claude-3-sonnet-20240229",
    "claude-3-haiku-20240307",
)
