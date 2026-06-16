"""Tests for the QAValidator agent's detect-improve cycle."""
import json
import unittest
from typing import Any
from unittest.mock import patch

from src.backend.agents.qa_validator import (
    _safe_issues_parse,
    _issues_text,
    _apply_fixes,
    _source_leak_count,
    _rejects_as_source_leak,
    _rejects_as_assistant_reply,
    _rejects_as_omission,
)


class TestQaValidatorHelpers(unittest.TestCase):
    """Test standalone helper functions."""

    def test_safe_issues_parse_empty(self) -> None:
        """Empty issues list should parse cleanly."""
        result = _safe_issues_parse('{"issues": []}')
        self.assertEqual(result, [])

    def test_safe_issues_parse_with_code_fence(self) -> None:
        """Should strip markdown code fences."""
        raw = '```json\n{"issues": []}\n```'
        result = _safe_issues_parse(raw)
        self.assertEqual(result, [])

    def test_safe_issues_parse_with_issues(self) -> None:
        """Should parse a full issues list."""
        raw = json.dumps({
            "issues": [
                {
                    "priority": "OMISSION",
                    "quote": "le monde",
                    "explanation": "Missing article",
                    "auto_fix": "le monde entier",
                },
                {
                    "priority": "FABRICATION",
                    "quote": "courut",
                    "explanation": "Not in source",
                    "auto_fix": "",
                },
            ]
        })
        result = _safe_issues_parse(raw)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["priority"], "OMISSION")
        self.assertEqual(result[1]["priority"], "FABRICATION")

    def test_safe_issues_parse_defaults_priority(self) -> None:
        """Unknown priority should default to REGISTER."""
        raw = json.dumps({
            "issues": [{"priority": "UNKNOWN", "quote": "test", "explanation": ""}]
        })
        result = _safe_issues_parse(raw)
        self.assertEqual(result[0]["priority"], "REGISTER")

    def test_safe_issues_parse_invalid_json_fallback(self) -> None:
        """Should fall back to regex extraction on broken JSON."""
        raw = 'Some text {"issues": [{"priority": "OMISSION", "quote": "x", "explanation": "y"}]} trailing'
        result = _safe_issues_parse(raw)
        self.assertEqual(len(result), 1)

    def test_safe_issues_parse_garbage(self) -> None:
        """Garbage text should produce empty list."""
        self.assertEqual(_safe_issues_parse("not even close"), [])

    def test_issues_text_formatting(self) -> None:
        """Should format issues as a readable bullet list."""
        issues = [
            {"priority": "FABRICATION", "quote": "arriva", "explanation": "Not in source", "auto_fix": "marcha"},
            {"priority": "OMISSION", "quote": "le", "explanation": "Missing", "auto_fix": ""},
            {"priority": "REGISTER", "quote": "bonjour", "explanation": "Too formal", "auto_fix": "salut"},
        ]
        text = _issues_text(issues)
        self.assertIn("FABRICATION", text)
        self.assertIn("arriva", text)
        self.assertIn("Suggested fix: marcha", text)
        self.assertIn("OMISSION", text)
        self.assertIn("REGISTER", text)
        self.assertIn("salut", text)

    def test_issues_text_skips_empty(self) -> None:
        """Entries with no quote or explanation should be skipped."""
        issues = [
            {"priority": "FABRICATION", "quote": "", "explanation": "", "auto_fix": ""},
        ]
        text = _issues_text(issues)
        self.assertEqual(text.strip(), "")

    def test_apply_fixes_simple(self) -> None:
        """Should replace quoted span with auto_fix."""
        issues = [
            {"priority": "OMISSION", "quote": "le monde", "explanation": "", "auto_fix": "le monde entier"},
        ]
        result = _apply_fixes("Bonjour le monde", issues)
        self.assertEqual(result, "Bonjour le monde entier")

    def test_apply_fixes_skips_register(self) -> None:
        """REGISTER issues should not be auto-applied."""
        issues = [
            {"priority": "REGISTER", "quote": "bonjour", "explanation": "", "auto_fix": "salut"},
        ]
        result = _apply_fixes("Bonjour le monde", issues)
        self.assertEqual(result, "Bonjour le monde")

    def test_apply_fixes_missing_quote(self) -> None:
        """Should skip fix if quote not found verbatim."""
        issues = [
            {"priority": "OMISSION", "quote": "nonexistent", "explanation": "", "auto_fix": "replacement"},
        ]
        result = _apply_fixes("Bonjour le monde", issues)
        self.assertEqual(result, "Bonjour le monde")

    def test_source_leak_count_normal(self) -> None:
        """Normal translation should have few leaks."""
        count = _source_leak_count("The fox jumps", "Le renard saute")
        self.assertLess(count, 2)

    def test_source_leak_count_high(self) -> None:
        """Translation with many source words verbatim should have high leaks."""
        count = _source_leak_count("The fox jumps over the dog", "The fox jumps over the dog")
        # 'fox', 'jumps', 'over', 'dog' — but 'over' is short (4 chars)
        # Actually re.findall(r"[A-Za-z][A-Za-z'-]{3,}" matches words >= 4 chars
        # 'fox' is 3 chars so won't match, 'jumps' is 5 chars ✓, 'over' is 4 chars ✓, 'dog' is 3 chars ✗
        # Also check exclusions: 'the' is excluded.
        # So source words: jumps, over
        # Translation words: jumps, over
        # Intersection: jumps, over -> 2
        self.assertGreaterEqual(count, 2)

    def test_rejects_as_source_leak(self) -> None:
        """Should reject if improved leaks more source words."""
        src = "The quick brown fox jumps over the lazy dog"
        current = "Le renard brun rapide saute par dessus le chien paresseux"
        improved = "The quick brown fox jumps over the lazy dog"  # full English
        self.assertTrue(_rejects_as_source_leak(src, current, improved))

    def test_rejects_as_assistant_reply(self) -> None:
        """Should reject chatty prefixes."""
        self.assertTrue(_rejects_as_assistant_reply("Bonjour", "Voici la traduction corrigée"))
        self.assertTrue(_rejects_as_assistant_reply("Bonjour", "Bien sûr, voici la version améliorée"))
        self.assertFalse(_rejects_as_assistant_reply("Bonjour", "Bonjour le monde"))

    def test_rejects_as_omission(self) -> None:
        """Should reject if improved is much shorter."""
        current = "This is a long translation that should be preserved in full without any cuts at all"
        improved = "Short"
        self.assertTrue(_rejects_as_omission(current, improved))

    def test_rejects_as_omission_acceptable(self) -> None:
        """Slight length variations should be fine."""
        current = "Bonjour le monde"
        improved = "Bonjour tout le monde"
        self.assertFalse(_rejects_as_omission(current, improved))


if __name__ == "__main__":
    unittest.main()
