"""Tests for translation profiles (CDC Phase 2)."""

from __future__ import annotations

from src.core.profiles import DEFAULT_PROFILE, PROFILE_NAMES, PROFILES, get_profile


def test_all_profiles_have_instruction_and_tone_word() -> None:
    for name, p in PROFILES.items():
        assert p["name"] == name
        assert isinstance(p["instruction"], str) and len(p["instruction"]) > 20
        assert isinstance(p["tone_word"], str) and p["tone_word"]


def test_profile_names_match_profiles() -> None:
    assert set(PROFILE_NAMES) == set(PROFILES.keys())


def test_expected_profiles_present() -> None:
    # CDC Phase 2: Technique, Littéraire, Courrier pro (+ a sensible default).
    assert "Technique" in PROFILES
    assert "Littéraire" in PROFILES
    assert "Courrier pro" in PROFILES
    assert "Général" in PROFILES


def test_get_profile_known() -> None:
    p = get_profile("Technique")
    assert p["name"] == "Technique"
    assert "technical" in p["instruction"].lower()


def test_get_profile_unknown_falls_back_to_default() -> None:
    p = get_profile("DoesNotExist")
    assert p["name"] == DEFAULT_PROFILE


def test_get_profile_none_falls_back_to_default() -> None:
    assert get_profile(None)["name"] == DEFAULT_PROFILE
    assert get_profile("")["name"] == DEFAULT_PROFILE


def test_instructions_are_distinct() -> None:
    instrs = {p["instruction"] for p in PROFILES.values()}
    assert len(instrs) == len(PROFILES)
