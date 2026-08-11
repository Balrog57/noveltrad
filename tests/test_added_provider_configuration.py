from pathlib import Path

from src.config import ANTHROPIC_API_ENDPOINT, XAI_API_ENDPOINT, NEXUM_API_ENDPOINT
from src.core.llm.providers.anthropic import AnthropicProvider
from src.core.llm.providers.xai import XAIProvider
from src.core.llm.providers.nexum import NexumProvider


def test_added_provider_endpoints_and_fallback_models():
    assert ANTHROPIC_API_ENDPOINT == "https://api.anthropic.com/v1"
    assert XAI_API_ENDPOINT == "https://api.x.ai/v1"
    assert NEXUM_API_ENDPOINT == "https://dialagram.me/router/v1"
    assert AnthropicProvider.API_URL.endswith("/v1/messages")
    assert "grok-4.5" in XAIProvider.FALLBACK_MODELS
    assert NexumProvider.FALLBACK_MODELS == ["qwen-3.7-max", "deepseek-v4", "xiaomi-mimo-2.5"]


def test_ui_nexum_fallback_contains_all_dialagram_models():
    source = (Path(__file__).parents[1] / "src/web/static/js/providers/provider-manager.js").read_text(encoding="utf-8")
    assert "xiaomi-mimo-2.5" in source
    assert "loadGenericCloudModels(provider)" in source
