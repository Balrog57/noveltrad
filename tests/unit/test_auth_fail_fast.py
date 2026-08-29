"""A 401 credential error must fail on the first attempt (issue #219)."""
from unittest.mock import AsyncMock

import pytest

from src.core.llm.providers.deepseek import DeepSeekProvider
from src.core.llm.providers.mistral import MistralProvider


class _UnauthorizedResponse:
    status_code = 401
    text = "invalid api key"

    def raise_for_status(self):
        raise AssertionError("401 must fail before raise_for_status")

    def json(self):
        raise AssertionError("401 must fail before parsing JSON")


class _CountingClient:
    def __init__(self):
        self.calls = 0

    async def post(self, *args, **kwargs):
        self.calls += 1
        return _UnauthorizedResponse()


@pytest.fixture
def no_sleep(monkeypatch):
    monkeypatch.setattr("asyncio.sleep", AsyncMock())


@pytest.mark.asyncio
async def test_mistral_invalid_key_does_not_retry(no_sleep):
    provider = MistralProvider(api_key="bad-key", model="mistral-small-latest")
    client = _CountingClient()
    provider._client = client

    result = await provider.generate("hello")

    assert result is None
    assert client.calls == 1


@pytest.mark.asyncio
async def test_deepseek_invalid_key_does_not_retry(no_sleep):
    provider = DeepSeekProvider(api_key="bad-key", model="deepseek-chat")
    client = _CountingClient()
    provider._client = client

    result = await provider.generate("hello")

    assert result is None
    assert client.calls == 1
