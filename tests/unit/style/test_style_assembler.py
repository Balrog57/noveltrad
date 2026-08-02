"""
Unit tests for assemble_instructions.

Verifies preamble selection per mode, line count/order, trailing-period
normalization, the empty-list contract, invalid-mode handling, the
anti-tic guard placement, that review-only fields (evidence, flags) never
leak into the assembled prose, and the `context` narrative-setting field:
the byte-identical contextless path, the "## Setting" section shape, and
that a context without rules still yields {None, None}.
"""
import pytest
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.core.style.assembler import (
    _ANTI_TIC_GUARD,
    _SETTING_GUARD,
    _TRANSLATION_PREAMBLE_MODEL,
    _TRANSLATION_PREAMBLE_SOURCE,
    assemble_instructions,
)

RULES = [
    {"dimension": "register", "instruction": "Keep the narrator emotionally detached",
     "evidence": "he watched without flinching", "flags": []},
    {"dimension": "sentence_rhythm", "instruction": "Alternate short and long sentences.",
     "evidence": "", "flags": []},
    {"dimension": "dialogue", "instruction": 'End some lines on a question mark?',
     "evidence": "", "flags": []},
]


class TestAssembleInstructionsPreambles:
    """1. source preamble, 2. model preamble."""

    def test_mode_source_block_starts_with_source_preamble(self):
        result = assemble_instructions("source", RULES)
        assert result["translation"].startswith(_TRANSLATION_PREAMBLE_SOURCE)

    def test_mode_model_block_starts_with_model_preamble(self):
        result = assemble_instructions("model", RULES)
        assert result["translation"].startswith(_TRANSLATION_PREAMBLE_MODEL)


class TestAssembleInstructionsBody:
    """3. line count/order, 4. trailing period, 8. evidence/flags never leak."""

    def test_line_count_matches_rule_count_and_order_is_preserved(self):
        result = assemble_instructions("source", RULES)
        body_lines = [
            line for line in result["translation"].split("\n") if line.startswith("- ")
        ]
        assert len(body_lines) == len(RULES)
        assert body_lines[0] == "- Keep the narrator emotionally detached."
        assert body_lines[1] == "- Alternate short and long sentences."
        assert body_lines[2] == "- End some lines on a question mark?"

    def test_instruction_without_final_period_gets_one(self):
        result = assemble_instructions("source", RULES)
        assert "- Keep the narrator emotionally detached." in result["translation"]

    def test_instruction_ending_in_question_mark_is_untouched(self):
        result = assemble_instructions("source", RULES)
        assert "- End some lines on a question mark?" in result["translation"]

    def test_instruction_ending_in_quote_is_untouched(self):
        rules = [{"instruction": 'Vary register the way one character says "please".'}]
        result = assemble_instructions("source", rules)
        assert '- Vary register the way one character says "please".' in result["translation"]

    def test_evidence_and_flags_never_appear_in_output(self):
        result = assemble_instructions("source", RULES)
        assert "he watched without flinching" not in result["translation"]
        assert "he watched without flinching" not in result["refinement"]


class TestAssembleInstructionsEdgeCases:
    """5. empty list, 6. bad mode, 7. anti-tic guard exactly once each."""

    def test_empty_rule_list_yields_both_none_and_no_guard(self):
        result = assemble_instructions("source", [])
        assert result == {"translation": None, "refinement": None}

    def test_rules_with_only_blank_instructions_yield_both_none(self):
        result = assemble_instructions("source", [{"instruction": "   "}])
        assert result == {"translation": None, "refinement": None}

    def test_bad_mode_raises_value_error(self):
        with pytest.raises(ValueError):
            assemble_instructions("bogus", RULES)

    def test_both_blocks_end_with_anti_tic_guard_exactly_once(self):
        result = assemble_instructions("source", RULES)
        assert result["translation"].endswith(_ANTI_TIC_GUARD)
        assert result["refinement"].endswith(_ANTI_TIC_GUARD)
        assert result["translation"].count(_ANTI_TIC_GUARD) == 1
        assert result["refinement"].count(_ANTI_TIC_GUARD) == 1


class TestAssembleInstructionsContext:
    """12. context blank -> byte-identical, 13. Setting section shape,
    14. guards appear exactly once, 15. context with no rules -> {None, None}."""

    def test_default_context_argument_is_byte_identical_to_two_arg_call(self):
        with_default = assemble_instructions("source", RULES)
        without_context_arg = assemble_instructions("source", RULES, context="")
        assert with_default == without_context_arg

    def test_blank_context_yields_byte_identical_output_to_no_context(self):
        no_context = assemble_instructions("source", RULES)
        blank_context = assemble_instructions("source", RULES, context="   \n  ")
        assert blank_context == no_context
        assert "## Setting" not in blank_context["translation"]
        assert _SETTING_GUARD not in blank_context["translation"]

    def test_non_empty_context_produces_setting_section_in_expected_order(self):
        result = assemble_instructions("source", RULES, context="A pre-industrial fishing village.")
        translation = result["translation"]

        preamble_pos = translation.index(_TRANSLATION_PREAMBLE_SOURCE)
        setting_heading_pos = translation.index("## Setting")
        context_pos = translation.index("A pre-industrial fishing village.")
        guard_pos = translation.index(_SETTING_GUARD)
        style_heading_pos = translation.index("## Style")
        body_pos = translation.index("- Keep the narrator emotionally detached.")
        anti_tic_pos = translation.index(_ANTI_TIC_GUARD)

        assert (
            preamble_pos
            < setting_heading_pos
            < context_pos
            < guard_pos
            < style_heading_pos
            < body_pos
            < anti_tic_pos
        )

    def test_context_is_stripped_before_insertion(self):
        result = assemble_instructions("source", RULES, context="  A frontier town.  \n")
        assert "\nA frontier town.\n" in result["translation"]
        assert "  A frontier town.  " not in result["translation"]

    def test_context_applies_to_both_translation_and_refinement_blocks(self):
        result = assemble_instructions("source", RULES, context="A frontier town.")
        assert "## Setting" in result["translation"]
        assert "## Setting" in result["refinement"]
        assert "A frontier town." in result["refinement"]

    def test_both_guards_appear_exactly_once_when_context_is_set(self):
        result = assemble_instructions("source", RULES, context="A frontier town.")
        assert result["translation"].count(_SETTING_GUARD) == 1
        assert result["translation"].count(_ANTI_TIC_GUARD) == 1
        assert result["refinement"].count(_SETTING_GUARD) == 1
        assert result["refinement"].count(_ANTI_TIC_GUARD) == 1

    def test_context_with_no_rules_still_yields_both_none(self):
        result = assemble_instructions("source", [], context="A frontier town.")
        assert result == {"translation": None, "refinement": None}

    def test_context_with_only_blank_instructions_still_yields_both_none(self):
        result = assemble_instructions("source", [{"instruction": "   "}], context="A frontier town.")
        assert result == {"translation": None, "refinement": None}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
