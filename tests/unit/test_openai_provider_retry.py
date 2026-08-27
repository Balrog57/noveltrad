"""OpenAICompatibleProvider retries empty and malformed 200s.

Aggregator routers (OpenRouter, OpenCode, …) often return HTTP 200 with
no usable text: empty ``content`` after billed reasoning, a 0-token drop, empty
``choices``, or a content-parts array. Those must be retried. An explicit
content-filter / refusal must not.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core.llm.providers.openai import OpenAICompatibleProvider
from src.core.llm.utils.openai_response import (
    parse_chat_completion,
    should_retry_empty_completion,
    stringify_message_content,
)


class _FakeResponse:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.calls = 0

    async def post(self, *args, **kwargs):
        self.calls += 1
        if not self.payloads:
            raise AssertionError("unexpected extra HTTP call")
        return _FakeResponse(self.payloads.pop(0))


def _payload(content, completion_tokens, finish_reason="stop", extra_message=None, choices=None):
    if choices is not None:
        body = {"choices": choices, "usage": {"prompt_tokens": 10, "completion_tokens": completion_tokens}}
        return body
    message = {"role": "assistant", "content": content}
    if extra_message:
        message.update(extra_message)
    return {
        "choices": [{"message": message, "finish_reason": finish_reason}],
        "usage": {"prompt_tokens": 10, "completion_tokens": completion_tokens},
    }


def _async_fake_client(provider, fake, monkeypatch):
    async def _get():
        return fake

    monkeypatch.setattr(provider, "_get_client", _get)


@pytest.fixture
def no_sleep(monkeypatch):
    async def _instant(_seconds):
        return None

    monkeypatch.setattr("src.core.llm.providers.openai.asyncio.sleep", _instant)


@pytest.mark.asyncio
async def test_retries_empty_content_when_tokens_were_billed(monkeypatch, no_sleep):
    provider = OpenAICompatibleProvider(
        api_endpoint="http://llm.test/v1", model="deepseek-v4", api_key="test-key"
    )
    fake = _FakeClient([
        _payload("", 8192),  # reasoning-only, empty answer
        _payload("Traduction correcte", 9000),
    ])
    _async_fake_client(provider, fake, monkeypatch)

    response = await provider.generate("Translate this", timeout=30)

    assert response is not None
    assert response.content == "Traduction correcte"
    assert fake.calls == 2


@pytest.mark.asyncio
async def test_retries_zero_token_empty_drop(monkeypatch, no_sleep):
    """A 0-token empty 200 is a router glitch, not a refusal — retry it."""
    provider = OpenAICompatibleProvider(
        api_endpoint="http://llm.test/v1", model="deepseek-v4", api_key="test-key"
    )
    fake = _FakeClient([
        _payload("", 0),
        _payload("Traduction correcte", 40),
    ])
    _async_fake_client(provider, fake, monkeypatch)

    response = await provider.generate("Translate this", timeout=30)

    assert response.content == "Traduction correcte"
    assert fake.calls == 2


@pytest.mark.asyncio
async def test_retries_empty_choices(monkeypatch, no_sleep):
    provider = OpenAICompatibleProvider(
        api_endpoint="http://llm.test/v1", model="qwen-3.7-max", api_key="test-key"
    )
    fake = _FakeClient([
        {"choices": [], "usage": {"prompt_tokens": 10, "completion_tokens": 0}},
        _payload("OK", 12),
    ])
    _async_fake_client(provider, fake, monkeypatch)

    response = await provider.generate("Translate this", timeout=30)

    assert response.content == "OK"
    assert fake.calls == 2


@pytest.mark.asyncio
async def test_retries_null_content(monkeypatch, no_sleep):
    provider = OpenAICompatibleProvider(
        api_endpoint="http://llm.test/v1", model="deepseek-v4", api_key="test-key"
    )
    fake = _FakeClient([
        _payload(None, 0),
        _payload("OK", 12),
    ])
    _async_fake_client(provider, fake, monkeypatch)

    response = await provider.generate("Translate this", timeout=30)

    assert response.content == "OK"
    assert fake.calls == 2


@pytest.mark.asyncio
async def test_extracts_text_from_content_parts(monkeypatch, no_sleep):
    provider = OpenAICompatibleProvider(
        api_endpoint="http://llm.test/v1", model="deepseek-v4", api_key="test-key"
    )
    fake = _FakeClient([
        _payload(
            [
                {"type": "reasoning", "text": "thinking..."},
                {"type": "text", "text": "Traduction correcte"},
            ],
            90,
        ),
    ])
    _async_fake_client(provider, fake, monkeypatch)

    response = await provider.generate("Translate this", timeout=30)

    assert response.content == "Traduction correcte"
    assert fake.calls == 1


@pytest.mark.asyncio
async def test_content_filter_is_not_retried(monkeypatch, no_sleep):
    provider = OpenAICompatibleProvider(
        api_endpoint="http://llm.test/v1", model="deepseek-v4", api_key="test-key"
    )
    fake = _FakeClient([_payload("", 0, finish_reason="content_filter")])
    _async_fake_client(provider, fake, monkeypatch)

    response = await provider.generate("Translate this", timeout=30)

    assert response is not None
    assert response.content == ""
    assert fake.calls == 1


@pytest.mark.asyncio
async def test_empty_retry_stops_at_attempt_limit(monkeypatch, no_sleep):
    monkeypatch.setattr("src.core.llm.providers.openai.MAX_TRANSLATION_ATTEMPTS", 2)
    provider = OpenAICompatibleProvider(
        api_endpoint="http://llm.test/v1", model="deepseek-v4", api_key="test-key"
    )
    fake = _FakeClient([
        _payload("", 6000),
        _payload("", 7000),
        _payload("should not be called", 10),
    ])
    _async_fake_client(provider, fake, monkeypatch)

    response = await provider.generate("Translate this", timeout=30)

    assert response is not None
    assert response.content == ""
    assert fake.calls == 2  # never exceeds MAX_TRANSLATION_ATTEMPTS default


@pytest.mark.asyncio
async def test_length_empty_stops_after_two_tries(monkeypatch, no_sleep):
    """finish_reason=length with no content must not loop five long calls."""
    provider = OpenAICompatibleProvider(
        api_endpoint="http://llm.test/v1", model="deepseek-v4", api_key="test-key"
    )
    fake = _FakeClient([
        _payload("", 10178, finish_reason="length"),
        _payload("", 8927, finish_reason="length"),
        _payload("should not be called", 10),
    ])
    _async_fake_client(provider, fake, monkeypatch)

    response = await provider.generate("Translate this", timeout=30)

    assert response is not None
    assert response.content == ""
    assert response.was_truncated is True
    assert fake.calls == 2


@pytest.mark.asyncio
async def test_connect_error_is_retried(monkeypatch, no_sleep):
    import httpx

    provider = OpenAICompatibleProvider(
        api_endpoint="http://llm.test/v1", model="deepseek-v4", api_key="test-key"
    )

    class _Flaky:
        def __init__(self):
            self.calls = 0

        async def post(self, *args, **kwargs):
            self.calls += 1
            if self.calls == 1:
                raise httpx.ConnectError("connection refused")
            return _FakeResponse(_payload("OK", 12))

    fake = _Flaky()
    _async_fake_client(provider, fake, monkeypatch)

    response = await provider.generate("Translate this", timeout=30)

    assert response.content == "OK"
    assert fake.calls == 2

    assert stringify_message_content(None) == ""
    assert stringify_message_content("hi") == "hi"
    assert stringify_message_content([
        {"type": "reasoning", "text": "nope"},
        {"type": "text", "text": "yes"},
    ]) == "yes"


def test_parse_explicit_refusal():
    parsed = parse_chat_completion(_payload("", 0, finish_reason="content_filter"))
    assert parsed["is_explicit_refusal"] is True
    assert should_retry_empty_completion(parsed, 0, 3) is False


def test_parse_zero_token_drop_is_retryable():
    parsed = parse_chat_completion(_payload("", 0, finish_reason="stop"))
    assert parsed["is_explicit_refusal"] is False
    assert should_retry_empty_completion(parsed, 0, 3) is True
    assert should_retry_empty_completion(parsed, 2, 3) is False
