"""OpenAI-compatible adapter (SDD 14.14).

The public OpenAI API is the reference cloud configuration of this third
adapter; an endpoint explicitly compatible with the Chat Completions
contract is also accepted. A 404/405 on /v1/models allows manual model
entry, afterwards verified by validate_configuration.
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
from .lm_studio import _map_finish


class OpenAICompatibleProvider:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or build_client()
        self._owns_client = client is None
        self._base = "https://api.openai.com/v1"
        self._api_key: str | None = None

    def set_api_key(self, api_key: str | None) -> None:
        self._api_key = api_key

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    async def validate_configuration(self, snapshot: PipelineSnapshot) -> ValidationReport:
        try:
            response = await self._client.get(
                f"{snapshot.base_url}/models", headers=self._headers()
            )
        except httpx.HTTPError as exc:
            return ValidationReport(
                False, ("PROVIDER_UNREACHABLE",), (f"provider unreachable: {exc}",)
            )
        if response.status_code in (404, 405):
            # manual model allowed; verify through a completion
            return ValidationReport(True, (), ())
        if response.status_code != 200:
            return ValidationReport(
                False, ("PROVIDER_ERROR",), (f"provider error: HTTP {response.status_code}",)
            )
        models = [m.get("id") for m in response.json().get("data", [])]
        if snapshot.model not in models:
            return ValidationReport(
                False, ("MODEL_NOT_FOUND",), (f"model {snapshot.model} not found",)
            )
        return ValidationReport(True, (), ())

    async def list_models(self) -> tuple[str, ...]:
        try:
            response = await self._client.get(f"{self._base}/models", headers=self._headers())
        except httpx.HTTPError as exc:
            raise ProviderError("PROVIDER_UNREACHABLE", False) from exc
        if response.status_code in (404, 405):
            raise ProviderError("MODELS_ENDPOINT_UNAVAILABLE", False)
        if response.status_code != 200:
            raise ProviderError("LIST_MODELS_FAILED", False)
        return tuple(m.get("id") for m in response.json().get("data", []))

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        payload = {
            "model": request.model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.payload_json},
            ],
            "stream": False,
            "temperature": request.temperature,
            "max_tokens": request.max_output_tokens,
        }
        try:
            response = await self._client.post(
                f"{self._base}/chat/completions", json=payload, headers=self._headers()
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
                    retry_after_seconds=parse_retry_after(response.headers.get("Retry-After")),
                    provider_request_id=None,
                )
            if response.status_code in (401, 403):
                raise ProviderError("AUTH_FAILED", False)
            raise ProviderError(
                "PROVIDER_ERROR", False, safe_message=f"provider error: HTTP {response.status_code}"
            )
        data = response.json()
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        text = message.get("content", "")
        usage = data.get("usage", {})
        return CompletionResponse(
            text=text,
            finish_reason=_map_finish(choice.get("finish_reason")),
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            retry_after_seconds=None,
            provider_request_id=data.get("id"),
        )

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()
