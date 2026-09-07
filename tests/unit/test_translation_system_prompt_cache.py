"""Tests for cached translation system prompt assembly."""
import pytest

from src.prompts.prompts import (
    _build_translation_system_prompt,
    _system_prompt_options_key,
    generate_translation_prompt,
)


def _common_kwargs():
    return {
        "context_before": "",
        "context_after": "",
        "previous_translation_context": "",
        "source_language": "English",
        "target_language": "French",
        "has_placeholders": True,
        "prompt_options": {"text_cleanup": True},
    }


def test_system_prompt_identical_across_chunks():
    """Chunk-varying fields must not change the cached system prompt."""
    kwargs = _common_kwargs()
    first = generate_translation_prompt(main_content="Chunk A.", **kwargs)
    second = generate_translation_prompt(main_content="Chunk B with different text.", **kwargs)
    assert first.system == second.system
    assert first.user != second.user


def test_system_prompt_cache_key_ignores_unrelated_options():
    """Unrelated prompt_options keys must not bust the system-prompt cache."""
    base = _system_prompt_options_key({"text_cleanup": True, "glossary_path": "/tmp/x"})
    with_extra = _system_prompt_options_key(
        {"text_cleanup": True, "glossary_path": "/tmp/y", "runtime_flag": 42}
    )
    assert base == with_extra


def test_system_prompt_cache_hit_on_repeated_calls():
    """Repeated jobs with the same settings should hit the lru_cache."""
    _build_translation_system_prompt.cache_clear()
    kwargs = _common_kwargs()
    for i in range(50):
        generate_translation_prompt(main_content=f"Chunk {i}.", **kwargs)
    info = _build_translation_system_prompt.cache_info()
    assert info.hits >= 49
    assert info.misses == 1


@pytest.mark.parametrize(
    "options_a,options_b,should_match",
    [
        ({}, {}, True),
        ({"custom_instructions": "Use formal tone."}, {"custom_instructions": "Use formal tone."}, True),
        ({"text_cleanup": True}, {"text_cleanup": False}, False),
        ({"plain_text_expected_paragraphs": 3}, {"plain_text_expected_paragraphs": 4}, False),
    ],
)
def test_system_prompt_options_key_distinguishes_relevant_fields(
    options_a, options_b, should_match
):
    key_a = _system_prompt_options_key(options_a)
    key_b = _system_prompt_options_key(options_b)
    if should_match:
        assert key_a == key_b
    else:
        assert key_a != key_b
