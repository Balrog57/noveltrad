"""
Unit tests for target_language_is_inflected.

Pins the membership contract of INFLECTED_TARGET_LANGUAGES: which target
languages get the glossary block's target-side inflection instruction, and
that the predicate is case-insensitive, regional-suffix tolerant and safe on
empty or None input.
"""
import pytest
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.core.glossary.inflection import (
    INFLECTED_TARGET_LANGUAGES,
    target_language_is_inflected,
)
from src.utils.lang_normalize import normalize_lang_key


class TestInflectedLanguages:
    """Languages that must receive the target-side inflection instruction."""

    def test_russian_capitalized(self):
        assert target_language_is_inflected("Russian") is True

    def test_russian_lowercase(self):
        assert target_language_is_inflected("russian") is True

    def test_serbian_with_parenthesised_suffix(self):
        """Exercises the parenthesised-suffix strip in normalize_lang_key only.

        Script choice is not this predicate's concern; this row must not be read
        as saying the two Serbian scripts are treated differently.
        """
        assert target_language_is_inflected("Serbian (Latin)") is True


class TestNonInflectedLanguages:
    """Languages deliberately excluded per design decision D2."""

    def test_chinese(self):
        assert target_language_is_inflected("Chinese") is False

    def test_korean(self):
        assert target_language_is_inflected("Korean") is False

    def test_bulgarian(self):
        """Slavic, but it lost nominal case declension."""
        assert target_language_is_inflected("Bulgarian") is False

    def test_arabic(self):
        """Excluded per D2: its case endings are unwritten diacritics, so they do
        not change the rendered string. Pinned so a later reader does not "fix"
        the omission.
        """
        assert target_language_is_inflected("Arabic") is False


class TestEdgeCases:
    """Empty, missing and unknown inputs."""

    def test_empty_string(self):
        assert target_language_is_inflected("") is False

    def test_none_does_not_raise(self):
        assert target_language_is_inflected(None) is False

    def test_unknown_language(self):
        assert target_language_is_inflected("Klingon") is False


class TestLanguageSetIntegrity:
    """The frozenset itself must already be in normalized form."""

    def test_every_entry_is_its_own_normalized_key(self):
        """Guards against someone adding a capitalized entry like "Russian"."""
        for entry in INFLECTED_TARGET_LANGUAGES:
            assert entry == normalize_lang_key(entry)

    def test_no_duplicate_after_normalization(self):
        normalized = [normalize_lang_key(e) for e in INFLECTED_TARGET_LANGUAGES]
        assert len(set(normalized)) == len(INFLECTED_TARGET_LANGUAGES)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
