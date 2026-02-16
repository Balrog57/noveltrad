"""Tests for the QAChecker module."""
import pytest
from src.core.qa_checker import QAChecker, QAIssue
from dataclasses import dataclass


@dataclass
class MockSegment:
    id: int
    index: int
    source_text: str
    target_text: str


@dataclass
class MockGlossaryTerm:
    source_term: str
    target_term: str


@pytest.fixture
def qa():
    return QAChecker()


class TestEmptyCheck:
    """Test empty/untranslated segment detection."""

    def test_untranslated(self, qa):
        segments = [MockSegment(1, 0, "Hello world.", "")]
        issues = qa.run_checks(segments, check_tags=False, check_numbers=False,
                               check_glossary=False, check_punctuation=False)
        assert len(issues) == 1
        assert issues[0].issue_type == 'empty_translation'

    def test_translated(self, qa):
        segments = [MockSegment(1, 0, "Hello.", "Bonjour.")]
        issues = qa.run_checks(segments, check_tags=False, check_numbers=False,
                               check_glossary=False, check_punctuation=False)
        assert len(issues) == 0


class TestTagCheck:
    """Test tag validation."""

    def test_missing_tag(self, qa):
        segments = [MockSegment(1, 0, "This is <b>bold</b>.", "Ceci est gras.")]
        issues = qa.run_checks(segments, check_numbers=False,
                               check_glossary=False, check_punctuation=False)
        assert any(i.issue_type == 'missing_tag' for i in issues)

    def test_valid_tags(self, qa):
        segments = [MockSegment(1, 0, "This is <b>bold</b>.", "Ceci est <b>gras</b>.")]
        issues = qa.run_checks(segments, check_numbers=False,
                               check_glossary=False, check_punctuation=False)
        tag_issues = [i for i in issues if i.issue_type in ('missing_tag', 'extra_tag')]
        assert len(tag_issues) == 0


class TestNumberCheck:
    """Test number consistency check."""

    def test_missing_number(self, qa):
        segments = [MockSegment(1, 0, "Chapter 42 is good.", "Le chapitre est bon.")]
        issues = qa.run_checks(segments, check_tags=False,
                               check_glossary=False, check_punctuation=False)
        assert any(i.issue_type == 'number_mismatch' for i in issues)

    def test_numbers_present(self, qa):
        segments = [MockSegment(1, 0, "Chapter 42.", "Chapitre 42.")]
        issues = qa.run_checks(segments, check_tags=False,
                               check_glossary=False, check_punctuation=False)
        number_issues = [i for i in issues if i.issue_type == 'number_mismatch']
        assert len(number_issues) == 0


class TestGlossaryCheck:
    """Test glossary term compliance."""

    def test_glossary_violation(self, qa):
        segments = [MockSegment(1, 0, "The cultivation technique.", "La méthode de combat.")]
        glossary = [MockGlossaryTerm("cultivation", "cultivation")]
        issues = qa.run_checks(segments, glossary_terms=glossary,
                               check_tags=False, check_numbers=False, check_punctuation=False)
        assert any(i.issue_type == 'glossary_violation' for i in issues)

    def test_glossary_respected(self, qa):
        segments = [MockSegment(1, 0, "The cultivation technique.", "La technique de cultivation.")]
        glossary = [MockGlossaryTerm("cultivation", "cultivation")]
        issues = qa.run_checks(segments, glossary_terms=glossary,
                               check_tags=False, check_numbers=False, check_punctuation=False)
        glossary_issues = [i for i in issues if i.issue_type == 'glossary_violation']
        assert len(glossary_issues) == 0


class TestPunctuationCheck:
    """Test trailing punctuation check."""

    def test_punctuation_mismatch(self, qa):
        segments = [MockSegment(1, 0, "Hello world.", "Bonjour le monde")]
        issues = qa.run_checks(segments, check_tags=False, check_numbers=False,
                               check_glossary=False)
        assert any(i.issue_type == 'punctuation_mismatch' for i in issues)

    def test_punctuation_match(self, qa):
        segments = [MockSegment(1, 0, "Hello world.", "Bonjour le monde.")]
        issues = qa.run_checks(segments, check_tags=False, check_numbers=False,
                               check_glossary=False)
        punct_issues = [i for i in issues if i.issue_type == 'punctuation_mismatch']
        assert len(punct_issues) == 0


class TestSummary:
    """Test QA summary generation."""

    def test_summary(self, qa):
        issues = [
            QAIssue(1, 0, 'empty_translation', 'warning', 'msg', 'src', ''),
            QAIssue(2, 1, 'missing_tag', 'error', 'msg', 'src', 'tgt'),
        ]
        summary = qa.get_summary(issues)
        assert summary['total'] == 2
        assert summary['by_severity']['error'] == 1
        assert summary['by_severity']['warning'] == 1
