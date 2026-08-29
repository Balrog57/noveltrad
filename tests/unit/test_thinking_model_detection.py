"""Thinking-model accessors must return booleans and arm Ollama detection (issue #220)."""
from unittest.mock import AsyncMock

import pytest

from src.core.llm.thinking.behavior import ThinkingBehavior
from src.core.llm_client import LLMClient


def test_gemini_accessor_returns_boolean_not_bound_method():
    client = LLMClient(provider_type="gemini", api_key="k", model="gemini-2.0-flash")
    client._get_provider()
    assert client.get_is_thinking_model() is False

    thinking = LLMClient(provider_type="gemini", api_key="k", model="gemini-2.5-pro")
    thinking._get_provider()
    assert thinking.get_is_thinking_model() is True


def test_deepseek_accessor_returns_boolean_not_bound_method():
    client = LLMClient(provider_type="deepseek", api_key="k", model="deepseek-chat")
    client._get_provider()
    assert client.get_is_thinking_model() is False


@pytest.mark.asyncio
async def test_ollama_detect_thinking_model_uses_behavior_api():
    client = LLMClient(
        provider_type="ollama",
        api_endpoint="http://127.0.0.1:11434/api/chat",
        model="llama3",
    )
    provider = client._get_provider()
    provider._detect_thinking_behavior = AsyncMock(
        return_value=ThinkingBehavior.CONTROLLABLE
    )

    result = await client.detect_thinking_model()

    provider._detect_thinking_behavior.assert_awaited_once()
    assert result is True
    assert client.get_is_thinking_model() is True
    assert provider._thinking_behavior == ThinkingBehavior.CONTROLLABLE
