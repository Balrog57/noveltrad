"""Tests for the Segmenter module."""
import pytest
from src.core.segmenter import Segmenter


@pytest.fixture
def segmenter():
    return Segmenter()


class TestLatinSegmentation:
    """Test segmentation of Latin-script text."""

    def test_simple_sentences(self, segmenter):
        text = "Hello world. How are you? I am fine!"
        result = segmenter.segment(text, lang='en')
        assert result == ["Hello world.", "How are you?", "I am fine!"]

    def test_single_sentence(self, segmenter):
        result = segmenter.segment("This is one sentence.", lang='en')
        assert result == ["This is one sentence."]

    def test_no_ending_punctuation(self, segmenter):
        result = segmenter.segment("No ending punctuation", lang='en')
        assert result == ["No ending punctuation"]

    def test_empty_text(self, segmenter):
        assert segmenter.segment("", lang='en') == []
        assert segmenter.segment("   ", lang='en') == []
        assert segmenter.segment(None, lang='en') == []

    def test_abbreviation_mr(self, segmenter):
        text = "Mr. Smith went home. He was tired."
        result = segmenter.segment(text, lang='en')
        assert result == ["Mr. Smith went home.", "He was tired."]

    def test_abbreviation_dr(self, segmenter):
        text = "Dr. Jones is here. She is a doctor."
        result = segmenter.segment(text, lang='en')
        assert result == ["Dr. Jones is here.", "She is a doctor."]

    def test_abbreviation_etc(self, segmenter):
        text = "Apples, oranges, etc. are fruits. They are healthy."
        result = segmenter.segment(text, lang='en')
        assert result == ["Apples, oranges, etc. are fruits.", "They are healthy."]

    def test_french_abbreviations(self, segmenter):
        text = "M. Dupont est arrivé. Il est content."
        result = segmenter.segment(text, lang='fr')
        assert result == ["M. Dupont est arrivé.", "Il est content."]

    def test_ellipsis(self, segmenter):
        text = "Wait... What happened? Nothing."
        result = segmenter.segment(text, lang='en')
        assert result == ["Wait...", "What happened?", "Nothing."]

    def test_unicode_ellipsis(self, segmenter):
        text = "Wait\u2026 What happened?"
        result = segmenter.segment(text, lang='en')
        assert result == ["Wait\u2026", "What happened?"]

    def test_quoted_ending(self, segmenter):
        text = 'He said "hello." She replied.'
        result = segmenter.segment(text, lang='en')
        assert len(result) == 2

    def test_number_dot(self, segmenter):
        text = "Chapter 1. The beginning starts here."
        result = segmenter.segment(text, lang='en')
        # "1." should not trigger a split
        assert len(result) == 1

    def test_multiple_paragraphs(self, segmenter):
        text = "First sentence. Second sentence!"
        result = segmenter.segment(text, lang='en')
        assert result == ["First sentence.", "Second sentence!"]


class TestCJKSegmentation:
    """Test segmentation of CJK text."""

    def test_chinese_simple(self, segmenter):
        text = "你好世界。你怎么样？我很好！"
        result = segmenter.segment(text, lang='zh')
        assert result == ["你好世界。", "你怎么样？", "我很好！"]

    def test_chinese_auto_detect(self, segmenter):
        """CJK text should be auto-detected even with lang='en'."""
        text = "你好世界。你怎么样？"
        result = segmenter.segment(text, lang='en')
        assert result == ["你好世界。", "你怎么样？"]

    def test_japanese(self, segmenter):
        text = "こんにちは。元気ですか？"
        result = segmenter.segment(text, lang='ja')
        assert result == ["こんにちは。", "元気ですか？"]

    def test_korean(self, segmenter):
        text = "안녕하세요. 잘 지내세요?"
        result = segmenter.segment(text, lang='ko')
        assert len(result) >= 1


class TestJoinSegments:
    """Test joining segments back together."""

    def test_join_default(self, segmenter):
        segments = ["Hello.", "World."]
        assert Segmenter.join_segments(segments) == "Hello.\nWorld."

    def test_join_custom_separator(self, segmenter):
        segments = ["Hello.", "World."]
        assert Segmenter.join_segments(segments, separator=' ') == "Hello. World."


class TestCustomAbbreviations:
    """Test custom abbreviation support."""

    def test_custom_abbreviation(self):
        custom = {'en': {'Corp', 'Inc'}}
        seg = Segmenter(custom_abbreviations=custom)
        text = "Corp. Smith is here. He works at Inc. today."
        result = seg.segment(text, lang='en')
        assert result == ["Corp. Smith is here.", "He works at Inc. today."]
