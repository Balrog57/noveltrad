"""
Unit tests for parse_style_response.

Verifies the permissive style-extraction JSON parser: tag extraction,
fence/object/array fallbacks, repair of trailing commas, dimension
coercion, instruction validation/truncation, deduplication, list capping,
the "never raises" contract, and the `context` narrative-setting field
(round-trip, default when absent, truncation with warning).
"""
import pytest
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.core.style.extractor import MAX_CONTEXT_CHARS, MAX_RULES, parse_style_response


def _rule(instruction="Alternate long subordinated sentences with short declarative ones.",
          dimension="sentence_rhythm", evidence=""):
    return {"dimension": dimension, "instruction": instruction, "evidence": evidence}


class TestParseStyleResponseBasic:
    """1. Well-formed tagged JSON."""

    def test_well_formed_tagged_json_yields_three_rules_no_warnings(self):
        raw = (
            '<STYLE_JSON>{"summary": "Dry noir prose.", "suggested_name": "dry_noir", '
            '"rules": ['
            '{"dimension": "register", "instruction": "Keep the narrator emotionally detached from violent events."},'
            '{"dimension": "sentence_rhythm", "instruction": "Alternate short declarative sentences with one longer one per paragraph."},'
            '{"dimension": "dialogue", "instruction": "Let characters answer questions with another question rather than a direct reply."}'
            ']}</STYLE_JSON>'
        )
        style, warnings = parse_style_response(raw)
        assert len(style["rules"]) == 3
        assert style["summary"] == "Dry noir prose."
        assert style["suggested_name"] == "dry_noir"
        assert warnings == []


class TestParseStyleResponseFallbacks:
    """2. Markdown fence, 9. bare array."""

    def test_markdown_fenced_json_without_tags_is_parsed_with_warning(self):
        raw = (
            'Here is the analysis:\n```json\n'
            '{"summary": "s", "suggested_name": "n", "rules": '
            '[{"dimension": "lexicon", "instruction": "Favor short concrete nouns over abstract ones."}]}'
            '\n```'
        )
        style, warnings = parse_style_response(raw)
        assert len(style["rules"]) == 1
        assert any("code fence" in w for w in warnings)

    def test_bare_json_array_is_accepted_as_rules_with_warning(self):
        raw = '[{"dimension": "imagery", "instruction": "Draw figurative language from a single sensory field."}]'
        style, warnings = parse_style_response(raw)
        assert len(style["rules"]) == 1
        assert style["summary"] == ""
        assert style["suggested_name"] == "extracted_style"
        assert any("bare JSON array" in w for w in warnings)


class TestParseStyleResponseThinkingAndRepair:
    """3. <think> stripping, 4. trailing-comma repair."""

    def test_thinking_block_before_payload_is_stripped(self):
        raw = (
            "<think>let me analyze the passages carefully</think>"
            '<STYLE_JSON>{"summary": "s", "suggested_name": "n", "rules": '
            '[{"dimension": "punctuation", "instruction": "Use em-dashes sparingly and only to mark a sudden break."}]}'
            '</STYLE_JSON>'
        )
        style, warnings = parse_style_response(raw)
        assert len(style["rules"]) == 1
        assert warnings == []

    def test_trailing_comma_is_repaired_with_warning(self):
        raw = (
            '<STYLE_JSON>{"summary": "s", "suggested_name": "n", "rules": '
            '[{"dimension": "formatting", "instruction": "Keep paragraphs short and break at every change of speaker.",},]}'
            '</STYLE_JSON>'
        )
        style, warnings = parse_style_response(raw)
        assert len(style["rules"]) == 1
        assert any("repaired" in w for w in warnings)


class TestParseStyleResponsePerRuleNormalization:
    """5. dimension coercion, 6. missing instruction, 7. dedup, 11. flags."""

    def test_unknown_dimension_is_coerced_to_other_with_warning(self):
        raw = (
            '<STYLE_JSON>{"summary": "s", "suggested_name": "n", "rules": '
            '[{"dimension": "vocabulary_choice", "instruction": "Keep sentences short and declarative throughout."}]}'
            '</STYLE_JSON>'
        )
        style, warnings = parse_style_response(raw)
        assert len(style["rules"]) == 1
        assert style["rules"][0]["dimension"] == "other"
        assert any("vocabulary_choice" in w and "other" in w for w in warnings)

    def test_rule_missing_instruction_is_skipped_with_warning(self):
        raw = (
            '<STYLE_JSON>{"summary": "s", "suggested_name": "n", "rules": '
            '[{"dimension": "register", "instruction": ""}, '
            '{"dimension": "lexicon", "instruction": "Prefer concrete nouns over abstract ones throughout."}]}'
            '</STYLE_JSON>'
        )
        style, warnings = parse_style_response(raw)
        assert len(style["rules"]) == 1
        assert any("skipped rule without 'instruction'" in w for w in warnings)

    def test_duplicate_instructions_differing_only_in_case_are_deduplicated_silently(self):
        raw = (
            '<STYLE_JSON>{"summary": "s", "suggested_name": "n", "rules": '
            '[{"dimension": "register", "instruction": "Keep the narrator emotionally detached at all times."}, '
            '{"dimension": "register", "instruction": "KEEP THE NARRATOR EMOTIONALLY DETACHED AT ALL TIMES."}]}'
            '</STYLE_JSON>'
        )
        style, warnings = parse_style_response(raw)
        assert len(style["rules"]) == 1
        assert not any("dup" in w.lower() for w in warnings)

    def test_every_rule_carries_a_flags_list(self):
        raw = (
            '<STYLE_JSON>{"summary": "s", "suggested_name": "n", "rules": '
            '[{"dimension": "register", "instruction": "Keep the narrator emotionally detached from violent events."}, '
            '{"dimension": "imagery", "instruction": "Use metaphors of darkness, such as \\"dusk\\" and \\"gloom\\"."}]}'
            '</STYLE_JSON>'
        )
        style, warnings = parse_style_response(raw)
        assert len(style["rules"]) == 2
        assert "flags" in style["rules"][0]
        assert style["rules"][0]["flags"] == []
        assert "quoted_example" in style["rules"][1]["flags"]
        assert "example_marker" in style["rules"][1]["flags"]


class TestParseStyleResponseTruncationAndFailure:
    """8. list capped at MAX_RULES, 10. garbage text never raises."""

    def test_sixty_rules_are_truncated_to_max_rules_with_warning(self):
        rules = [
            {"dimension": "other", "instruction": f"Apply stylistic tendency number {i} consistently throughout."}
            for i in range(60)
        ]
        import json
        raw = f'<STYLE_JSON>{{"summary": "s", "suggested_name": "n", "rules": {json.dumps(rules)}}}</STYLE_JSON>'
        style, warnings = parse_style_response(raw)
        assert len(style["rules"]) == MAX_RULES
        assert any("truncated" in w and str(MAX_RULES) in w for w in warnings)

    def test_garbage_text_yields_empty_rules_and_warning_without_raising(self):
        raw = "lorem ipsum dolor sit amet, no json here at all"
        style, warnings = parse_style_response(raw)
        assert style["rules"] == []
        assert style["summary"] == ""
        assert style["suggested_name"] == "extracted_style"
        assert len(warnings) >= 1

    def test_empty_input_never_raises(self):
        style, warnings = parse_style_response("")
        assert style == {"summary": "", "suggested_name": "extracted_style", "context": "", "rules": []}
        assert warnings == ["empty LLM response"]

    def test_unrepairable_json_never_raises(self):
        raw = '<STYLE_JSON>{"rules": [{"instruction":</STYLE_JSON>'
        style, warnings = parse_style_response(raw)
        assert style["rules"] == []
        assert any("json parse error" in w.lower() for w in warnings)


class TestParseStyleResponseContext:
    """12. context round-trip, 13. missing-context default, 14. truncation with warning."""

    def test_context_round_trips_stripped(self):
        raw = (
            '<STYLE_JSON>{"summary": "s", "suggested_name": "n", '
            '"context": "  A pre-industrial fishing village under feudal law.  ", '
            '"rules": [{"dimension": "register", "instruction": "Keep the narrator emotionally detached."}]}'
            '</STYLE_JSON>'
        )
        style, warnings = parse_style_response(raw)
        assert style["context"] == "A pre-industrial fishing village under feudal law."
        assert warnings == []

    def test_missing_context_defaults_to_empty_string(self):
        raw = (
            '<STYLE_JSON>{"summary": "s", "suggested_name": "n", '
            '"rules": [{"dimension": "register", "instruction": "Keep the narrator emotionally detached."}]}'
            '</STYLE_JSON>'
        )
        style, warnings = parse_style_response(raw)
        assert style["context"] == ""
        assert warnings == []

    def test_bare_array_root_yields_empty_context(self):
        raw = '[{"dimension": "imagery", "instruction": "Draw figurative language from a single sensory field."}]'
        style, warnings = parse_style_response(raw)
        assert style["context"] == ""

    def test_oversized_context_is_truncated_with_warning(self):
        long_context = "A " + ("very " * 200) + "old kingdom."
        assert len(long_context) > MAX_CONTEXT_CHARS
        raw = (
            '<STYLE_JSON>{"summary": "s", "suggested_name": "n", '
            f'"context": "{long_context}", '
            '"rules": [{"dimension": "register", "instruction": "Keep the narrator emotionally detached."}]}'
            '</STYLE_JSON>'
        )
        style, warnings = parse_style_response(raw)
        assert len(style["context"]) <= MAX_CONTEXT_CHARS
        assert any("truncated context" in w and str(MAX_CONTEXT_CHARS) in w for w in warnings)

    def test_empty_input_result_includes_empty_context_key(self):
        style, warnings = parse_style_response("")
        assert style["context"] == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
