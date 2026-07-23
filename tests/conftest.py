"""Shared test fixtures.

A fake LLM (FakeChatModel) implementing the LangChain BaseChatModel surface
just enough for the agent nodes. It returns canned, CDC-shaped responses, so
tests never hit a real Ollama server.
"""

from __future__ import annotations

from typing import Any

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from src.core import agents as _agents_mod


class FakeChatModel(BaseChatModel):
    """Returns a scripted response per call, cycling through a list.

    Each entry in ``responses`` is either a plain string (raw content) or a
    callable(prompt) -> str so tests can tailor the reply to the prompt.
    """

    responses: list[Any] = []
    _index: int = 0

    def _generate(self, messages: list[BaseMessage], stop=None, **kwargs) -> ChatResult:  # noqa: ANN001, ARG002
        prompt = "\n".join(str(m.content) for m in messages)
        idx = min(self._index, len(self.responses) - 1)
        entry = self.responses[idx]
        self._index += 1
        content = entry(prompt) if callable(entry) else entry
        msg = AIMessage(content=content)
        return ChatResult(generations=[ChatGeneration(message=msg)])

    @property
    def _llm_type(self) -> str:
        return "fake"

    def bind(self, **kwargs: Any):  # type: ignore[override]
        # The agents call .bind(response_format=...) for JSON mode. The fake
        # ignores it and returns whatever scripted response is queued.
        return self


@pytest.fixture
def fake_llm_factory():
    """Returns a factory that builds a FakeChatModel AND injects it as active LLM.

    The returned model is also set via agents.set_llm() so the pipeline nodes
    pick it up. The autouse reset fixture below clears it after each test.
    """
    def _factory(responses: list[Any]) -> FakeChatModel:
        model = FakeChatModel(responses=responses)  # type: ignore[arg-type]
        _agents_mod.set_llm(model)
        return model
    return _factory


@pytest.fixture(autouse=True)
def _reset_active_llm():
    """Ensure no LLM leaks between tests (avoids accidental Ollama calls)."""
    _agents_mod.set_llm(None)
    yield
    _agents_mod.set_llm(None)
