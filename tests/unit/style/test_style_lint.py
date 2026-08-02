"""
Table-driven unit tests for lint_instruction.

One case per abstraction-violation code, plus negatives, plus a guard test
that the four assembled preambles and the anti-tic guard (which are shipped
verbatim to every translation/refinement prompt) lint clean themselves.
"""
import pytest
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.core.style.lint import lint_instruction
from src.core.style.assembler import (
    _ANTI_TIC_GUARD,
    _REFINEMENT_PREAMBLE_MODEL,
    _REFINEMENT_PREAMBLE_SOURCE,
    _TRANSLATION_PREAMBLE_MODEL,
    _TRANSLATION_PREAMBLE_SOURCE,
)

CASES = [
    (
        'Use metaphors of darkness, such as "dusk" and "gloom".',
        {"quoted_example", "example_marker"},
    ),
    (
        "Favor concrete nouns: rain, iron, dust, smoke.",
        {"word_list"},
    ),
    (
        "Write like Raymond Chandler.",
        {"proper_noun"},
    ),
    (
        "Use short words.",
        {"too_specific"},
    ),
    (
        "Draw figurative language from a single consistent sensory field rather than "
        "varying its source from one image to the next.",
        set(),
    ),
    (
        "Alternate long subordinated sentences with abrupt declarative ones, keeping the "
        "abrupt ones in the minority.",
        set(),
    ),
    (
        "Translate into English with a formal register.",
        set(),
    ),
]


@pytest.mark.parametrize("instruction,expected_flags", CASES)
def test_lint_instruction_table(instruction, expected_flags):
    assert set(lint_instruction(instruction)) == expected_flags


def test_flags_returned_in_deterministic_order_for_multi_flag_case():
    flags = lint_instruction('Use metaphors of darkness, such as "dusk" and "gloom".')
    assert flags == ["quoted_example", "example_marker"]


def test_empty_string_yields_no_flags():
    assert lint_instruction("") == []


@pytest.mark.parametrize(
    "preamble",
    [
        _TRANSLATION_PREAMBLE_SOURCE,
        _TRANSLATION_PREAMBLE_MODEL,
        _REFINEMENT_PREAMBLE_SOURCE,
        _REFINEMENT_PREAMBLE_MODEL,
        _ANTI_TIC_GUARD,
    ],
)
def test_assembled_preambles_lint_clean(preamble):
    """
    Guard against a regex that fires on the templates themselves — the
    preambles and the anti-tic guard are shipped verbatim to every prompt,
    so they must never self-flag.
    """
    assert lint_instruction(preamble) == []


@pytest.mark.parametrize(
    "preamble",
    [_TRANSLATION_PREAMBLE_SOURCE, _TRANSLATION_PREAMBLE_MODEL,
     _REFINEMENT_PREAMBLE_SOURCE, _REFINEMENT_PREAMBLE_MODEL],
)
def test_preamble_plus_anti_tic_guard_lints_clean(preamble):
    """Same guard, but on the concatenated block as it is actually shipped."""
    block = f"{preamble}\n\n{_ANTI_TIC_GUARD}"
    assert lint_instruction(block) == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
