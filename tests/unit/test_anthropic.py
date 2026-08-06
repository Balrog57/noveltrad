"""Unit tests for the Anthropic (Claude) adapter."""

from __future__ import annotations

import json

import pytest

from noveltrad.core.contracts import (
    CompletionRequest,
    FinishReason,
    PipelineSnapshot,
    PipelineStage,
    SegmentId,
)
from noveltrad.core.exceptions import ProviderError
from noveltrad.modules.translation.providers.anthropic import AnthropicProvider


class _FakeTransport:
    """httpx transport double returning canned responses."""

    def __init__(self, responses: list[dict]) -> None:
        self.responses = responses
        self.requests: list[dict] = []

    async def handle_async_request(self, request):
        self.requests.append(
            {"url": str(request.url), "headers": dict(request.headers), "body": request.content}
        )
        payload = self.responses.pop(0)
        import httpx

        return httpx.Response(payload["status"], json=payload["json"], request=request)


def _snapshot() -> PipelineSnapshot:
    return PipelineSnapshot(
        provider="anthropic",
        base_url="https://api.anthropic.com",
        model="claude-sonnet-4-20250514",
        context_window_tokens=8192,
        tokenizer_id="utf8-bytes-v1",
        temperature=0.2,
        max_output_tokens=1024,
        seed=None,
        prompt_bundle_version="v1",
        response_schema_version="v1",
        snapshot_hash="x",
    )


def _provider(responses: list[dict]) -> tuple[AnthropicProvider, _FakeTransport]:
    import httpx

    transport = _FakeTransport(responses)
    client = httpx.AsyncClient(transport=transport)
    provider = AnthropicProvider(client=client)
    provider.set_api_key("sk-ant-test")
    return provider, transport


@pytest.mark.asyncio
async def test_complete_parses_text_blocks():
    provider, transport = _provider(
        [
            {
                "status": 200,
                "json": {
                    "id": "msg_01",
                    "content": [{"type": "text", "text": "Bonjour le monde."}],
                    "stop_reason": "end_turn",
                    "usage": {"input_tokens": 12, "output_tokens": 5},
                },
            }
        ]
    )
    request = CompletionRequest(
        request_id="r1",
        segment_id=SegmentId(1),
        stage=PipelineStage.TRANSLATE,
        system_prompt="You are a translator.",
        payload_json=json.dumps({"target_content": "Hello world."}),
        model="claude-sonnet-4-20250514",
        temperature=0.2,
        max_output_tokens=1024,
    )
    response = await provider.complete(request)
    assert response.text == "Bonjour le monde."
    assert response.finish_reason == FinishReason.STOP
    assert response.input_tokens == 12
    assert response.output_tokens == 5
    sent = json.loads(transport.requests[0]["body"])
    assert sent["model"] == "claude-sonnet-4-20250514"
    assert sent["max_tokens"] == 1024
    assert transport.requests[0]["headers"]["x-api-key"] == "sk-ant-test"
    assert "anthropic-version" in transport.requests[0]["headers"]
    await provider.close()


@pytest.mark.asyncio
async def test_complete_auth_error_is_permanent():
    provider, _ = _provider([{"status": 401, "json": {"error": "unauthorized"}}])
    request = CompletionRequest(
        request_id="r2",
        segment_id=SegmentId(1),
        stage=PipelineStage.TRANSLATE,
        system_prompt="s",
        payload_json="{}",
        model="claude-sonnet-4-20250514",
        temperature=0.2,
        max_output_tokens=8,
    )
    with pytest.raises(ProviderError) as exc_info:
        await provider.complete(request)
    assert exc_info.value.error_code == "AUTH_FAILED"
    assert exc_info.value.recoverable is False
    await provider.close()


@pytest.mark.asyncio
async def test_complete_429_is_recoverable():
    provider, _ = _provider([{"status": 429, "json": {"error": "rate limited"}}])
    request = CompletionRequest(
        request_id="r3",
        segment_id=SegmentId(1),
        stage=PipelineStage.TRANSLATE,
        system_prompt="s",
        payload_json="{}",
        model="claude-sonnet-4-20250514",
        temperature=0.2,
        max_output_tokens=8,
    )
    response = await provider.complete(request)
    assert response.finish_reason == FinishReason.OTHER
    assert response.text == ""
    await provider.close()


@pytest.mark.asyncio
async def test_validate_requires_api_key():
    provider, _ = _provider([])
    provider.set_api_key(None)
    report = await provider.validate_configuration(_snapshot())
    assert not report.valid
    assert "API_KEY_MISSING" in report.error_codes
    await provider.close()


@pytest.mark.asyncio
async def test_list_models_returns_known_models():
    from noveltrad.modules.translation.providers.anthropic import _KNOWN_MODELS

    provider, _ = _provider([])
    models = await provider.list_models()
    assert "claude-sonnet-4-20250514" in models
    assert models == _KNOWN_MODELS
    await provider.close()
