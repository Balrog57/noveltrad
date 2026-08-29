"""Issue #231: LLM-layer correctness (pricing, Gemini parts, cache, thinking, Ollama)."""
import time

from src.core.llm.providers.gemini import join_gemini_text_parts
from src.core.llm.providers.ollama import OllamaProvider
from src.core.llm.thinking.behavior import ThinkingBehavior
from src.core.llm.thinking.cache import ThinkingCache
from src.core.llm.thinking.detection import detect_repetition_loop
from src.core.llm.utils.context_detection import ContextDetector
from src.core.pricing.pricing_data import get_default_pricing


def test_pricing_longest_model_key_wins():
    lite = get_default_pricing("gemini", "gemini-2.5-flash-lite")
    flash = get_default_pricing("gemini", "gemini-2.5-flash")
    assert lite is not None and flash is not None
    assert lite["input"] != flash["input"]
    dated = get_default_pricing("openai", "gpt-4o-2024-08-06")
    gpt4 = get_default_pricing("openai", "gpt-4")
    assert dated["input"] == get_default_pricing("openai", "gpt-4o")["input"]
    assert dated["input"] != gpt4["input"]


def test_gemini_joins_all_text_parts():
    assert join_gemini_text_parts([
        {"text": "Hello "},
        {"thought": True},
        {"text": "world"},
    ]) == "Hello world"
    assert join_gemini_text_parts([]) == ""
    assert join_gemini_text_parts(None) == ""


def test_thinking_cache_stores_wall_clock(tmp_path):
    cache = ThinkingCache(tmp_path / "thinking.json")
    before = time.time()
    cache.set("qwen3:14b", ThinkingBehavior.STANDARD, endpoint="http://localhost")
    after = time.time()
    entry = cache._cache["qwen3:14b@http://localhost"]
    assert before <= entry["tested_at"] <= after


def test_long_phrase_repetition_uses_stricter_threshold():
    phrase = "The same forty-character looping text!!!"
    assert len(phrase) >= 40
    text = phrase * 4
    # Pass-40 branch needs 3 repeats; the unreachable old >=20 branch needed 5.
    assert detect_repetition_loop(text, min_phrase_length=5, min_repetitions=3) is True


def test_ollama_provider_owns_context_detector():
    provider = OllamaProvider(model="qwen3:14b")
    assert isinstance(provider._context_detector, ContextDetector)
