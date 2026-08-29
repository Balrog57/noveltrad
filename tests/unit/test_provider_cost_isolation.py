"""OpenRouter and Poe cost tracking must be per instance (issue #218)."""
from unittest.mock import AsyncMock

import pytest

from src.core.llm.providers.openrouter import OpenRouterProvider
from src.core.llm.providers.poe import PoeProvider


class _FakeResponse:
    status_code = 200

    def __init__(self, payload, captured=None):
        self._payload = payload
        self._captured = captured

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self, payload, captured=None):
        self.payload = payload
        self.captured = captured if captured is not None else {}
        self.calls = 0

    async def post(self, url, headers=None, json=None, timeout=None):
        self.calls += 1
        self.captured["url"] = url
        self.captured["json"] = json
        return _FakeResponse(self.payload, self.captured)


def _openrouter_payload(text="ok", prompt=10, completion=5, cost=None, usage_cost=None):
    usage = {"prompt_tokens": prompt, "completion_tokens": completion}
    if usage_cost is not None:
        usage["cost"] = usage_cost
    body = {
        "choices": [{"message": {"content": text}, "finish_reason": "stop"}],
        "usage": usage,
    }
    if cost is not None:
        body["cost"] = cost
    return body


@pytest.mark.asyncio
async def test_openrouter_cost_is_isolated_between_instances():
    """Two concurrent jobs must not share session cost or the callback."""
    seen_a = []
    seen_b = []
    a = OpenRouterProvider(api_key="key-a", model="test/model")
    b = OpenRouterProvider(api_key="key-b", model="test/model")
    a._cost_callback = lambda data: seen_a.append(data["session_cost"])
    b._cost_callback = lambda data: seen_b.append(data["session_cost"])

    payload = _openrouter_payload(cost=0.25)
    a._client = _FakeClient(payload)
    b._client = _FakeClient(payload)

    await a.generate("hello")
    await a.generate("hello")
    await b.generate("hello")

    cost_a, tokens_a = a.get_session_cost()
    cost_b, tokens_b = b.get_session_cost()
    assert cost_a == pytest.approx(0.50)
    assert cost_b == pytest.approx(0.25)
    assert tokens_a["prompt"] == 20
    assert tokens_b["prompt"] == 10
    assert seen_a == [pytest.approx(0.25), pytest.approx(0.50)]
    assert seen_b == [pytest.approx(0.25)]


@pytest.mark.asyncio
async def test_openrouter_requests_usage_and_prefers_reported_cost():
    """OpenRouter must ask for usage so the real cost is used when present."""
    captured = {}
    provider = OpenRouterProvider(api_key="key", model="test/model")
    provider._client = _FakeClient(
        _openrouter_payload(prompt=1000, completion=2000, usage_cost=0.0042),
        captured,
    )

    await provider.generate("hello")

    assert captured["json"]["usage"] == {"include": True}
    cost, _ = provider.get_session_cost()
    assert cost == pytest.approx(0.0042)


@pytest.mark.asyncio
async def test_poe_token_totals_are_isolated_between_instances(monkeypatch):
    monkeypatch.setattr(
        PoeProvider, "_get_bot_overrides", AsyncMock(return_value={})
    )
    a = PoeProvider(api_key="key-a", model="Test-Bot")
    b = PoeProvider(api_key="key-b", model="Test-Bot")
    payload = {
        "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 7, "completion_tokens": 3},
    }
    a._client = _FakeClient(payload)
    b._client = _FakeClient(payload)

    await a.generate("hello")
    await a.generate("hello")
    await b.generate("hello")

    _, tokens_a = a.get_session_cost()
    _, tokens_b = b.get_session_cost()
    assert tokens_a == {"prompt": 14, "completion": 6}
    assert tokens_b == {"prompt": 7, "completion": 3}
