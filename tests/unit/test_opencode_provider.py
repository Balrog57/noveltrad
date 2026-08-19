"""OpenCode Zen/Go inject a generous completion budget and disable thinking."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core.llm.factory import create_llm_provider
from src.core.llm.providers.opencode import OpenCodeGoProvider, OpenCodeProvider


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
        self.last_url = None

    async def post(self, url, *args, **kwargs):
        self.calls += 1
        self.last_url = url
        self.last_json = kwargs.get("json")
        return _FakeResponse({
            "choices": [{"message": {"role": "assistant", "content": "Hallo"}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 3},
        })


def _async_fake_client(provider, fake, monkeypatch):
    async def _get():
        return fake

    monkeypatch.setattr(provider, "_get_client", _get)


@pytest.mark.parametrize("provider_cls", [OpenCodeProvider, OpenCodeGoProvider])
@pytest.mark.asyncio
async def test_generate_sets_default_max_tokens_and_disables_thinking(monkeypatch, provider_cls):
    provider = provider_cls(api_key="test-key", model="deepseek-v4-flash")
    fake = _FakeClient()
    _async_fake_client(provider, fake, monkeypatch)

    await provider.generate("Translate", timeout=30)

    assert fake.calls == 1
    assert fake.last_json["max_tokens"] == provider_cls.DEFAULT_MAX_OUTPUT_TOKENS
    assert fake.last_json["thinking"] == {"type": "disabled"}
    assert "enable_thinking" not in fake.last_json
    assert fake.last_url.endswith("/chat/completions")


@pytest.mark.parametrize("provider_cls", [OpenCodeProvider, OpenCodeGoProvider])
@pytest.mark.asyncio
async def test_generate_keeps_explicit_max_tokens(monkeypatch, provider_cls):
    provider = provider_cls(api_key="test-key", model="deepseek-v4-flash")
    fake = _FakeClient()
    _async_fake_client(provider, fake, monkeypatch)

    await provider.generate("Translate", timeout=30, max_tokens=1234)

    assert fake.last_json["max_tokens"] == 1234


def test_opencode_go_falls_back_to_zen_key(monkeypatch):
    monkeypatch.delenv("OPENCODE_GO_API_KEY", raising=False)
    monkeypatch.setenv("OPENCODE_API_KEY", "zen-shared-key")

    provider = create_llm_provider("opencodego", api_key="", model="deepseek-v4-pro")

    assert isinstance(provider, OpenCodeGoProvider)
    assert provider.api_key == "zen-shared-key"
