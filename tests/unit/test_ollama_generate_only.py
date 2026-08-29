"""Hy-MT2 and other specialized MT models speak Ollama /api/generate, not /api/chat."""
import asyncio
import json

from src.core.llm.providers.ollama import OllamaProvider, _is_generate_only_model
from src.core.llm.thinking.behavior import ThinkingBehavior


class _FakeResponse:
    def __init__(self, lines):
        self._lines = lines

    def raise_for_status(self):
        return None

    async def aiter_lines(self):
        for line in self._lines:
            yield line

    async def aclose(self):
        return None


class _FakeCM:
    def __init__(self, lines):
        self._lines = lines

    async def __aenter__(self):
        return _FakeResponse(self._lines)

    async def __aexit__(self, *args):
        return False


class _FakeClient:
    def __init__(self, lines):
        self._lines = lines
        self.last_url = None
        self.last_payload = None

    def stream(self, method, url, json=None, timeout=None):
        self.last_url = url
        self.last_payload = json
        return _FakeCM(self._lines)


def test_hy_mt2_is_generate_only_by_name():
    assert _is_generate_only_model("hy-mt2:1.8b")
    assert _is_generate_only_model("hunyuan-mt:7b")
    assert not _is_generate_only_model("qwen3:14b")


def test_hy_mt2_keeps_generate_endpoint():
    provider = OllamaProvider(
        api_endpoint="http://localhost:11434/api/generate",
        model="hy-mt2:1.8b",
    )
    assert provider.api_endpoint.endswith("/api/generate")


def test_chat_models_still_rewrite_generate_to_chat():
    provider = OllamaProvider(
        api_endpoint="http://localhost:11434/api/generate",
        model="qwen3:14b",
    )
    assert provider.api_endpoint.endswith("/api/chat")


def test_generate_only_parses_ollama_response_field():
    lines = [
        json.dumps({"model": "hy-mt2:1.8b", "response": "Bonjour", "done": False}),
        json.dumps({
            "model": "hy-mt2:1.8b",
            "response": "",
            "done": True,
            "prompt_eval_count": 12,
            "eval_count": 2,
        }),
    ]
    provider = OllamaProvider(
        api_endpoint="http://localhost:11434/api/generate",
        model="hy-mt2:1.8b",
    )
    provider._thinking_behavior = ThinkingBehavior.STANDARD
    provider._supports_think_param = False
    client = _FakeClient(lines)

    async def _fake_get_client():
        return client

    provider._get_client = _fake_get_client
    result = asyncio.run(provider.generate("Hello", system_prompt="Translate to French."))
    assert result is not None
    assert result.content == "Bonjour"
    assert client.last_url.endswith("/api/generate")
    assert "prompt" in client.last_payload
    assert "messages" not in client.last_payload
    assert "think" not in client.last_payload
