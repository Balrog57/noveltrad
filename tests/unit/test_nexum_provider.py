"""NexumProvider injects a generous completion budget by default."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core.llm.providers.nexum import NexumProvider


class _FakeResponse:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self):
        self.calls = 0
        self.last_json = None

    async def post(self, *args, **kwargs):
        self.calls += 1
        self.last_json = kwargs.get("json")
        return _FakeResponse({
            "choices": [{"message": {"role": "assistant", "content": "Hallo"}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 3},
        })


def _async_fake_client(provider, fake, monkeypatch):
    async def _get():
        return fake

    monkeypatch.setattr(provider, "_get_client", _get)


@pytest.mark.asyncio
async def test_generate_sets_default_max_tokens(monkeypatch):
    provider = NexumProvider(api_key="test-key", model="deepseek-v4")
    fake = _FakeClient()
    _async_fake_client(provider, fake, monkeypatch)

    await provider.generate("Translate", timeout=30)

    assert fake.calls == 1
    assert fake.last_json["max_tokens"] == NexumProvider.DEFAULT_MAX_OUTPUT_TOKENS
    assert fake.last_json["thinking"] == {"type": "disabled"}
    assert "enable_thinking" not in fake.last_json


@pytest.mark.asyncio
async def test_generate_keeps_explicit_max_tokens(monkeypatch):
    provider = NexumProvider(api_key="test-key", model="deepseek-v4")
    fake = _FakeClient()
    _async_fake_client(provider, fake, monkeypatch)

    await provider.generate("Translate", timeout=30, max_tokens=1234)

    assert fake.last_json["max_tokens"] == 1234
    assert fake.last_json["thinking"] == {"type": "disabled"}


@pytest.mark.asyncio
async def test_qwen_does_not_send_thinking_struct(monkeypatch):
    provider = NexumProvider(api_key="test-key", model="qwen-3.7-max")
    fake = _FakeClient()
    _async_fake_client(provider, fake, monkeypatch)

    await provider.generate("Translate", timeout=30)

    assert "thinking" not in fake.last_json
    assert "enable_thinking" not in fake.last_json


@pytest.mark.asyncio
async def test_nexum_retries_zero_token_empty_beyond_global_default(monkeypatch):
    """Nexum uses MAX_GENERATE_ATTEMPTS=5 so a flaky Dialagram drop is retried."""
    from src.core.llm.providers import openai as openai_mod

    monkeypatch.setattr(openai_mod, "MAX_TRANSLATION_ATTEMPTS", 2)

    async def _instant(_seconds):
        return None

    monkeypatch.setattr(openai_mod.asyncio, "sleep", _instant)

    provider = NexumProvider(api_key="test-key", model="deepseek-v4")
    fake = _FakeClient()
    payloads = [
        {"choices": [{"message": {"content": ""}}], "usage": {"prompt_tokens": 1, "completion_tokens": 0}},
        {"choices": [{"message": {"content": ""}}], "usage": {"prompt_tokens": 1, "completion_tokens": 0}},
        {"choices": [{"message": {"content": "Hallo"}}], "usage": {"prompt_tokens": 5, "completion_tokens": 3}},
    ]

    async def _post(*args, **kwargs):
        fake.calls += 1
        fake.last_json = kwargs.get("json")
        return _FakeResponse(payloads.pop(0))

    fake.post = _post
    _async_fake_client(provider, fake, monkeypatch)

    response = await provider.generate("Translate", timeout=30)

    assert fake.calls == 3
    assert response.content == "Hallo"
    assert NexumProvider.MAX_GENERATE_ATTEMPTS == 5