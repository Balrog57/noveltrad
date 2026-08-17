"""OpenAICompatibleProvider retries empty responses that still billed tokens.

A reasoning model behind an OpenAI-compatible router (e.g. deepseek-v4 on
Dialagram) sometimes returns HTTP 200 with an empty ``content`` after its
chain-of-thought consumed the completion budget. The provider must retry such
responses instead of handing an empty translation to the pipeline, while a
genuine zero-token refusal must NOT be retried (it will not recover).
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core.llm.providers.openai import OpenAICompatibleProvider


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
        return _FakeResponse(self.payloads.pop(0))


def _payload(content, completion_tokens):
    return {
        "choices": [{"message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": completion_tokens},
    }


def _async_fake_client(provider, fake, monkeypatch):
    async def _get():
        return fake

    monkeypatch.setattr(provider, "_get_client", _get)


@pytest.mark.asyncio
async def test_retries_empty_content_when_tokens_were_billed(monkeypatch):
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
async def test_empty_retry_stops_at_attempt_limit(monkeypatch):
    provider = OpenAICompatibleProvider(
        api_endpoint="http://llm.test/v1", model="deepseek-v4", api_key="test-key"
    )
    fake = _FakeClient([
        _payload("", 6000),
        _payload("", 7000),
    ])
    _async_fake_client(provider, fake, monkeypatch)

    response = await provider.generate("Translate this", timeout=30)

    assert response is not None
    assert response.content == ""
    assert fake.calls == 2  # never exceeds MAX_TRANSLATION_ATTEMPTS


@pytest.mark.asyncio
async def test_zero_token_refusal_is_not_retried(monkeypatch):
    provider = OpenAICompatibleProvider(
        api_endpoint="http://llm.test/v1", model="deepseek-v4", api_key="test-key"
    )
    fake = _FakeClient([_payload("", 0)])
    _async_fake_client(provider, fake, monkeypatch)

    response = await provider.generate("Translate this", timeout=30)

    assert response is not None
    assert response.content == ""
    assert fake.calls == 1