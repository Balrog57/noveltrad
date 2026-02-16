"""Tests for the Aligner module."""
import pytest
from src.core.aligner import Aligner, AlignedPair


@pytest.fixture
def aligner():
    return Aligner()


class TestBasicAlignment:
    """Test basic text alignment."""

    def test_simple_1to1(self, aligner):
        source = "Hello world. How are you?"
        target = "Bonjour le monde. Comment allez-vous?"
        pairs = aligner.align(source, target, src_lang='en', tgt_lang='fr')
        assert len(pairs) == 2
        assert pairs[0].source == "Hello world."
        assert pairs[1].source == "How are you?"

    def test_empty_texts(self, aligner):
        assert aligner.align("", "", src_lang='en', tgt_lang='fr') == []
        assert aligner.align(None, None, src_lang='en', tgt_lang='fr') == []

    def test_single_sentence(self, aligner):
        source = "Hello world."
        target = "Bonjour le monde."
        pairs = aligner.align(source, target, src_lang='en', tgt_lang='fr')
        assert len(pairs) == 1
        assert pairs[0].source == "Hello world."
        assert pairs[0].target == "Bonjour le monde."

    def test_confidence_scores(self, aligner):
        source = "Hello world."
        target = "Bonjour le monde."
        pairs = aligner.align(source, target, src_lang='en', tgt_lang='fr')
        assert all(0.0 <= p.confidence <= 1.0 for p in pairs)


class TestSegmentAlignment:
    """Test alignment of pre-segmented lists."""

    def test_equal_length(self, aligner):
        source = ["First.", "Second.", "Third."]
        target = ["Premier.", "Deuxième.", "Troisième."]
        pairs = aligner.align_segments(source, target)
        assert len(pairs) == 3

    def test_empty_lists(self, aligner):
        assert aligner.align_segments([], []) == []


class TestExport:
    """Test export to TMX data."""

    def test_export_pairs(self, aligner):
        pairs = [
            AlignedPair("Hello.", "Bonjour.", 0.9, [0], [0]),
            AlignedPair("World.", "Monde.", 0.8, [1], [1]),
        ]
        data = aligner.export_pairs_as_tmx_data(pairs)
        assert len(data) == 2
        assert data[0] == ("Hello.", "Bonjour.")
