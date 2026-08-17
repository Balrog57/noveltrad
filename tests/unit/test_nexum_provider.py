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


@pytest.mark.asyncio
async def test_generate_keeps_explicit_max_tokens(monkeypatch):
    provider = NexumProvider(api_key="test-key", model="deepseek-v4")
    fake = _FakeClient()
    _async_fake_client(provider, fake, monkeypatch)

    await provider.generate("Translate", timeout=30, max_tokens=1234)

    assert fake.last_json["max_tokens"] == 1234