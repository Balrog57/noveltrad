"""
Unit tests for generate_style_extraction_prompt.

Verifies the prompt builder produces two distinct modes, enumerates all
style dimensions, declares the required STYLE tags, embeds the sampled
text verbatim, enforces the English-only instruction-language directive
regardless of source/target languages, states the abstraction directive
(five prohibitions plus the rejected/accepted contrast pair), and states
the per-mode `context` (narrative-setting) requirement: mode "source"
asks for it, mode "model" demands the empty string with its rationale.
"""
import pytest
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.prompts.prompts import (
    generate_style_extraction_prompt,
    PromptPair,
    STYLE_TAG_IN,
    STYLE_TAG_OUT,
)
from src.config import INPUT_TAG_IN, INPUT_TAG_OUT

DIMENSION_LABELS = (
    "register",
    "narrative_voice",
    "sentence_rhythm",
    "lexicon",
    "imagery",
    "dialogue",
    "punctuation",
    "formatting",
)

PROHIBITION_MARKERS = (
    "quotation marks at all",
    "example words, phrases, idioms",
    "such as",
    "proper nouns, no invented terminology",
    "one specific token",
)

REJECTED_EXAMPLE = 'Use metaphors of darkness and shadow, and words like "dusk" and "gloom".'
ACCEPTED_EXAMPLE = (
    "Draw figurative language from a single consistent sensory field "
    "rather than varying its source from one image to the next."
)


class TestGenerateStyleExtractionPrompt:
    """Tests for the style extraction prompt builder."""

    def test_returns_prompt_pair_with_non_empty_fields(self):
        """Returns a PromptPair with non-empty system and user prompts."""
        prompt = generate_style_extraction_prompt("Some sample text", mode="source")
        assert isinstance(prompt, PromptPair)
        assert prompt.system
        assert prompt.user

    def test_both_modes_produce_different_system_prompts(self):
        """The 'source' and 'model' modes yield different system prompts."""
        source_prompt = generate_style_extraction_prompt("Some sample text", mode="source")
        model_prompt = generate_style_extraction_prompt("Some sample text", mode="model")
        assert source_prompt.system != model_prompt.system

    def test_bogus_mode_raises_value_error(self):
        """An unknown mode raises ValueError."""
        with pytest.raises(ValueError):
            generate_style_extraction_prompt("Some sample text", mode="bogus")

    @pytest.mark.parametrize("mode", ["source", "model"])
    def test_all_dimension_labels_present(self, mode):
        """All 8 dimension labels appear in the system prompt."""
        prompt = generate_style_extraction_prompt("Some sample text", mode=mode)
        for label in DIMENSION_LABELS:
            assert label in prompt.system, f"missing dimension '{label}' in system prompt"

    @pytest.mark.parametrize("mode", ["source", "model"])
    def test_style_tags_present(self, mode):
        """Both STYLE_JSON tags appear in the system prompt."""
        prompt = generate_style_extraction_prompt("Some sample text", mode=mode)
        assert STYLE_TAG_IN in prompt.system
        assert STYLE_TAG_OUT in prompt.system
        assert prompt.user
        assert STYLE_TAG_IN in prompt.user or STYLE_TAG_IN in prompt.system

    def test_sampled_text_present_verbatim_in_user_prompt(self):
        """The sampled text appears verbatim between INPUT_TAG_IN/OUT in the user prompt."""
        text = "The quick brown fox jumps over the lazy dog."
        prompt = generate_style_extraction_prompt(text, mode="source")
        assert INPUT_TAG_IN in prompt.user
        assert INPUT_TAG_OUT in prompt.user
        start = prompt.user.index(INPUT_TAG_IN) + len(INPUT_TAG_IN)
        end = prompt.user.index(INPUT_TAG_OUT)
        assert start < end
        assert text in prompt.user[start:end]

    def test_long_input_text_is_preserved_fully(self):
        """The prompt builder does not truncate long input text (truncation is upstream)."""
        long_text = "A" * 50000
        prompt = generate_style_extraction_prompt(long_text, mode="source")
        assert long_text in prompt.user

    def test_english_directive_present_for_chinese_to_french_pair(self):
        """
        The instruction-language directive says 'English' even for a
        Chinese -> French pair, proving it is not parameterized by
        source_language/target_language.
        """
        prompt = generate_style_extraction_prompt(
            "一些示例文本",
            mode="source",
            source_language="Chinese",
            target_language="French",
        )
        assert "English" in prompt.system
        assert "Write every instruction in English" in prompt.system

    @pytest.mark.parametrize("mode", ["source", "model"])
    def test_abstraction_directive_prohibition_markers_present(self, mode):
        """All five prohibition markers of the abstraction directive appear."""
        prompt = generate_style_extraction_prompt("Some sample text", mode=mode)
        for marker in PROHIBITION_MARKERS:
            assert marker in prompt.system, f"missing prohibition marker '{marker}' in system prompt"

    @pytest.mark.parametrize("mode", ["source", "model"])
    def test_abstraction_directive_contrast_pair_present(self, mode):
        """Both halves of the rejected/accepted contrast pair are reproduced verbatim."""
        prompt = generate_style_extraction_prompt("Some sample text", mode=mode)
        assert REJECTED_EXAMPLE in prompt.system
        assert ACCEPTED_EXAMPLE in prompt.system

    def test_source_mode_states_target_language(self):
        """In 'source' mode, the target language is stated so the model knows the destination."""
        prompt = generate_style_extraction_prompt(
            "Some sample text", mode="source", source_language="Chinese", target_language="French"
        )
        assert "Chinese" in prompt.user
        assert "French" in prompt.user

    def test_model_mode_states_passages_already_in_target_language(self):
        """In 'model' mode, the user prompt states the passages are already in the target language."""
        prompt = generate_style_extraction_prompt(
            "Some sample text", mode="model", source_language="Chinese", target_language="French"
        )
        assert "French" in prompt.user


class TestGenerateStyleExtractionPromptContextField:
    """Per-mode requirement for the new `context` (narrative-setting) field."""

    def test_context_key_declared_in_schema_for_both_modes(self):
        for mode in ("source", "model"):
            prompt = generate_style_extraction_prompt("Some sample text", mode=mode)
            assert '"context"' in prompt.system

    def test_source_mode_requires_context_with_bounds_and_rationale(self):
        """Mode 'source' asks for a bounded, English, era/tech/social description with a rationale."""
        prompt = generate_style_extraction_prompt("Some sample text", mode="source")
        system = prompt.system
        assert "CONTEXT FIELD" in system
        assert "1 to 3 sentences" in system
        assert "400 characters" in system
        assert "historical period" in system
        assert "technological level" in system
        assert "social and cultural frame" in system
        assert "proper nouns, character names, place names" in system
        assert "summary of the plot" in system
        assert "later era" in system or "different technological level" in system

    def test_model_mode_demands_empty_string_with_rationale(self):
        """Mode 'model' requires the empty string and explains why: the reference work's
        setting must not be imposed on the unrelated text being translated."""
        prompt = generate_style_extraction_prompt("Some sample text", mode="model")
        system = prompt.system
        assert "CONTEXT FIELD" in system
        assert 'MUST be the empty string ""' in system
        assert "stylistic model" in system
        assert "must never be imposed" in system

    def test_source_and_model_context_directives_differ(self):
        source_prompt = generate_style_extraction_prompt("Some sample text", mode="source")
        model_prompt = generate_style_extraction_prompt("Some sample text", mode="model")
        assert "1 to 3 sentences" not in model_prompt.system
        assert 'MUST be the empty string' not in source_prompt.system

    def test_source_mode_example_context_is_non_empty(self):
        prompt = generate_style_extraction_prompt("Some sample text", mode="source")
        assert '"context": "",' not in prompt.system

    def test_model_mode_example_context_is_empty_string(self):
        prompt = generate_style_extraction_prompt("Some sample text", mode="model")
        assert '"context": "",' in prompt.system


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
