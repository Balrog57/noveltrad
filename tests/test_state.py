"""Tests for the TranslationState TypedDict (CDC §2)."""

from src.core.state import TranslationState, make_initial_state


def test_make_initial_state_has_required_cdc_fields() -> None:
    state = make_initial_state(
        source_text="Hello world.",
        source_lang="Anglais",
        target_lang="Français",
        profile="Général",
    )
    # CDC §2 inputs
    assert state["source_text"] == "Hello world."
    assert state["source_lang"] == "Anglais"
    assert state["target_lang"] == "Français"
    assert state["profile"] == "Général"
    assert state["glossary"] == {}

    # CDC §2 intermediate outputs (start None)
    assert state["draft_translation"] is None
    assert state["corrected_text"] is None
    assert state["edits_made"] is None
    assert state["glossary_applied_text"] is None

    # CDC §2 final outputs (start None)
    assert state["final_text"] is None
    assert state["status"] is None

    # CDC §2 logs feed the inspector
    assert state["logs"] == []


def test_make_initial_state_accepts_glossary() -> None:
    state = make_initial_state(
        source_text="x",
        source_lang="Anglais",
        target_lang="Français",
        glossary={"bug": "anomalie"},
    )
    assert state["glossary"] == {"bug": "anomalie"}


def test_typeddict_is_a_plain_dict() -> None:
    """TranslationState must behave like a dict for LangGraph state merging."""
    state: TranslationState = make_initial_state("x", "Anglais", "Français")
    assert isinstance(state, dict)
    merged = {**state, "draft_translation": "X", "logs": state["logs"] + ["l"]}
    assert merged["draft_translation"] == "X"
    assert merged["logs"] == ["l"]
