"""Tests for the agent nodes (CDC §3 prompts + JSON output schemas).

These verify that:
  - the prompts format with CDC placeholders,
  - the JSON outputs are parsed into the Pydantic models with EXACT CDC field
    names (corrected_text, edits_made, glossary_matches, fidelity_score, flags…),
  - the validator's final_text is surfaced (the bug the TS app had).
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from src.core.agents import (
    PROOFREADER_SYSTEM,
    TRANSLATOR_SYSTEM,
    VALIDATOR_SYSTEM,
    draft_translator_node,
    glossary_node,
    proofreader_node,
    validator_node,
)
from src.core.state import make_initial_state
from src.core.validators import (
    GlossaryOutput,
    ProofreadOutput,
    ValidatorOutput,
)

# --------------------------------------------------------------------------- #
# Prompt formatting (CDC placeholders)
# --------------------------------------------------------------------------- #


def test_translator_prompt_formats_with_cdc_placeholders() -> None:
    out = TRANSLATOR_SYSTEM.format(
        source_lang="Anglais",
        target_lang="Français",
        tone="Professional",
        source_text="Hello world.",
    )
    assert "Anglais" in out and "Français" in out
    assert "Hello world." in out
    # JSON example braces survived literal (doubled in source).
    assert "{" not in out  # translator has no JSON block


def test_proofreader_prompt_keeps_json_block_literal() -> None:
    out = PROOFREADER_SYSTEM.format(
        source_lang="Anglais", target_lang="Français", tone="Professional",
        source_text="Hello", draft_translation="Bonjour",
    )
    assert '"corrected_text"' in out
    assert '"edits_made"' in out


def test_validator_prompt_keeps_json_block_literal() -> None:
    out = VALIDATOR_SYSTEM.format(
        source_lang="Anglais", target_lang="Français",
        source_text="Hello", candidate_text="Bonjour",
    )
    assert '"fidelity_score"' in out
    assert '"final_text"' in out
    assert '"flags"' in out


# --------------------------------------------------------------------------- #
# Validators parse exact CDC field names
# --------------------------------------------------------------------------- #


def test_proofread_output_cdc_fields() -> None:
    parsed = ProofreadOutput.model_validate({
        "corrected_text": "Bonjour le monde.",
        "edits_made": [
            {"type": "Fluency", "original_phrase": "Bonjour", "revised_phrase": "Bonjour le monde.",
             "reason": "completed the sentence"},
        ],
    })
    assert parsed.corrected_text == "Bonjour le monde."
    assert parsed.edits_made[0].type == "Fluency"


def test_glossary_output_cdc_fields() -> None:
    parsed = GlossaryOutput.model_validate({
        "final_glossary_applied_text": "Une anomalie est survenue.",
        "glossary_matches": [
            {"source_term": "bug", "forced_target_term": "anomalie", "status": "Applied"},
        ],
    })
    assert parsed.glossary_matches[0].forced_target_term == "anomalie"


def test_validator_output_cdc_fields_and_score_bounds() -> None:
    parsed = ValidatorOutput.model_validate({
        "status": "PASSED_WITH_CORRECTIONS",
        "fidelity_score": 97,
        "final_text": "Final text.",
        "flags": [{"severity": "Low", "issue": "x", "resolution": "y"}],
    })
    assert parsed.fidelity_score == 97
    assert parsed.flags[0].severity == "Low"

    # Out-of-range score rejected.
    with pytest.raises(ValidationError):
        ValidatorOutput.model_validate({"status": "PASSED", "fidelity_score": 150,
                                        "final_text": "x", "flags": []})


# --------------------------------------------------------------------------- #
# Node behaviour with a fake LLM
# --------------------------------------------------------------------------- #


def _config():
    return {"recursion_limit": 25}


def test_translator_node_returns_raw_text(fake_llm_factory) -> None:
    fake_llm_factory(["Bonjour le monde."])
    state = make_initial_state("Hello world.", "Anglais", "Français")
    out = draft_translator_node(state, _config())
    assert out["draft_translation"] == "Bonjour le monde."
    assert out["logs"] and "translator" in out["logs"][0]


def test_proofreader_node_parses_cdc_json(fake_llm_factory) -> None:
    payload = {
        "corrected_text": "Bonjour le monde.",
        "edits_made": [
            {"type": "Grammar", "original_phrase": "bonjour", "revised_phrase": "Bonjour",
             "reason": "capitalisation"},
        ],
    }
    fake_llm_factory([json.dumps(payload)])
    state = make_initial_state("Hello", "Anglais", "Français")
    state["draft_translation"] = "bonjour"
    out = proofreader_node(state, _config())
    assert out["corrected_text"] == "Bonjour le monde."
    assert len(out["edits_made"]) == 1
    assert out["edits_made"][0]["type"] == "Grammar"


def test_proofreader_node_tolerates_json_fence(fake_llm_factory) -> None:
    payload = {"corrected_text": "Ok.", "edits_made": []}
    fake_llm_factory(["```json\n" + json.dumps(payload) + "\n```"])
    state = make_initial_state("Hello", "Anglais", "Français")
    state["draft_translation"] = "ok"
    out = proofreader_node(state, _config())
    assert out["corrected_text"] == "Ok."


def test_glossary_node_applies_terms(fake_llm_factory) -> None:
    payload = {
        "final_glossary_applied_text": "Une anomalie est survenue.",
        "glossary_matches": [
            {"source_term": "bug", "forced_target_term": "anomalie", "status": "Applied"},
        ],
    }
    fake_llm_factory([json.dumps(payload)])
    state = make_initial_state("A bug occurred.", "Anglais", "Français",
                               glossary={"bug": "anomalie"})
    state["corrected_text"] = "Un bug est survenu."
    out = glossary_node(state, _config())
    assert out["glossary_applied_text"] == "Une anomalie est survenue."
    assert out["glossary_matches"][0]["forced_target_term"] == "anomalie"


def test_validator_node_surfaces_final_text_and_score(fake_llm_factory) -> None:
    """CDC integration tip: validator final_text is THE pipeline result.

    This is the exact behaviour the TS app failed at (CDC_GAP_ANALYSIS P0-1).
    """
    payload = {
        "status": "PASSED",
        "fidelity_score": 95,
        "final_text": "Bonjour le monde.",
        "flags": [],
    }
    fake_llm_factory([json.dumps(payload)])
    state = make_initial_state("Hello world.", "Anglais", "Français")
    state["glossary_applied_text"] = "Bonjour le monde."
    out = validator_node(state, _config())
    assert out["final_text"] == "Bonjour le monde."
    assert out["fidelity_score"] == 95
    assert out["status"] == "PASSED"
