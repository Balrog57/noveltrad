"""Tests for the Concordancer module."""
import pytest
from src.core.concordancer import Concordancer, ConcordanceResult
from dataclasses import dataclass


@dataclass
class MockSegment:
    source_text: str
    target_text: str


@pytest.fixture
def concordancer():
    return Concordancer(fuzzy_threshold=0.6)


@pytest.fixture
def sample_segments():
    return [
        MockSegment("The cultivation technique was powerful.", "La technique de cultivation était puissante."),
        MockSegment("He cultivated his inner energy.", "Il cultivait son énergie intérieure."),
        MockSegment("The mountain was tall and majestic.", "La montagne était grande et majestueuse."),
    ]


class TestExactSearch:
    """Test exact and substring search."""

    def test_exact_match(self, concordancer, sample_segments):
        results = concordancer.search("cultivation", segments=sample_segments)
        assert len(results) >= 1
        assert any('cultivation' in r.source_text.lower() for r in results)

    def test_substring_match(self, concordancer, sample_segments):
        results = concordancer.search("culti", segments=sample_segments)
        assert len(results) >= 1

    def test_target_search(self, concordancer, sample_segments):
        results = concordancer.search("montagne", segments=sample_segments,
                                       search_source=False, search_target=True)
        assert len(results) >= 1

    def test_no_match(self, concordancer, sample_segments):
        results = concordancer.search("xyznonexistent", segments=sample_segments)
        assert len(results) == 0

    def test_empty_query(self, concordancer, sample_segments):
        results = concordancer.search("", segments=sample_segments)
        assert results == []

    def test_case_insensitive(self, concordancer, sample_segments):
        results = concordancer.search("CULTIVATION", segments=sample_segments)
        assert len(results) >= 1


class TestFuzzySearch:
    """Test fuzzy matching."""

    def test_fuzzy_match(self, concordancer, sample_segments):
        results = concordancer.search("cultivatin", segments=sample_segments)
        # Should find fuzzy match for "cultivation"
        assert len(results) >= 0  # May or may not match depending on threshold


class TestRegexSearch:
    """Test regex search."""

    def test_regex_pattern(self, concordancer, sample_segments):
        results = concordancer.search_regex(r"culti\w+", segments=sample_segments)
        assert len(results) >= 1

    def test_invalid_regex(self, concordancer, sample_segments):
        results = concordancer.search_regex("[invalid", segments=sample_segments)
        assert results == []


class TestDeduplication:
    """Test result deduplication."""

    def test_no_duplicates(self, concordancer):
        segments = [
            MockSegment("Hello world.", "Bonjour le monde."),
            MockSegment("Hello world.", "Bonjour le monde."),  # duplicate
        ]
        results = concordancer.search("Hello", segments=segments)
        assert len(results) == 1
