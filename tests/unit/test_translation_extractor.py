"""
Unit tests for TranslationExtractor (issue #170 fixes)
"""
import pytest
from src.core.llm.utils.extraction import TranslationExtractor


class TestTranslationExtractor:
    def test_basic_extraction(self):
        extractor = TranslationExtractor("<TRANSLATION>", "</TRANSLATION>")
        result = extractor.extract("<TRANSLATION>Hello world</TRANSLATION>")
        assert result == "Hello world"

    def test_extraction_with_whitespace(self):
        extractor = TranslationExtractor("<TRANSLATION>", "</TRANSLATION>")
        result = extractor.extract("  <TRANSLATION>  Hello world  </TRANSLATION>  ")
        assert result == "Hello world"

    def test_think_blocks_removed(self):
        extractor = TranslationExtractor("<TRANSLATION>", "</TRANSLATION>")
        result = extractor.extract(
            "<think>Some reasoning</think><TRANSLATION>Hello</TRANSLATION>"
        )
        assert result == "Hello"

    def test_orphan_think_before_translation_is_stripped(self):
        """Orphan </think> before <TRANSLATION> should be stripped."""
        extractor = TranslationExtractor("<TRANSLATION>", "</TRANSLATION>")
        raw = "Some reasoning...</think>\n<TRANSLATION>Hello</TRANSLATION>"
        result = extractor.extract(raw)
        assert result == "Hello"

    def test_orphan_think_inside_translation_is_preserved(self):
        """Issue #170 fix: orphan </think> inside translation must NOT destroy the tag."""
        extractor = TranslationExtractor("<TRANSLATION>", "</TRANSLATION>")
        raw = "<TRANSLATION>\nHello world\n</think>"
        result = extractor.extract(raw)
        # Prefix contains <TRANSLATION>, so the orphan remover must not wipe
        # the body; the unclosed tag is salvaged instead.
        assert result == "Hello world"

    def test_orphan_think_inside_translation_content_preserved(self):
        """Ensure the raw content is still inspectable after failed extraction."""
        extractor = TranslationExtractor("<TRANSLATION>", "</TRANSLATION>")
        raw = "<TRANSLATION>\nLe renard brun\n</think>"
        result = extractor.extract(raw)
        assert result == "Le renard brun"
        assert "<TRANSLATION>" in raw
        assert "Le renard brun" in raw

    def test_markdown_fence_stripping(self):
        extractor = TranslationExtractor("<TRANSLATION>", "</TRANSLATION>")
        result = extractor.extract("```xml\n<TRANSLATION>Hello</TRANSLATION>\n```")
        assert result == "Hello"

    def test_no_tags_returns_none(self):
        extractor = TranslationExtractor("<TRANSLATION>", "</TRANSLATION>")
        result = extractor.extract("Just some text without tags")
        assert result is None

    def test_unclosed_opening_tag_is_salvaged(self):
        extractor = TranslationExtractor("<TRANSLATION>", "</TRANSLATION>")
        result = extractor.extract("<TRANSLATION> incomplete")
        assert result == "incomplete"

    def test_unclosed_tag_with_preamble_is_salvaged(self):
        extractor = TranslationExtractor("<TRANSLATION>", "</TRANSLATION>")
        result = extractor.extract(
            "Sure!\n<TRANSLATION> «C'est tout — pour une civilisation"
        )
        assert result == "«C'est tout — pour une civilisation"

    def test_unclosed_tag_case_insensitive(self):
        extractor = TranslationExtractor("<TRANSLATION>", "</TRANSLATION>")
        result = extractor.extract("<translation>Bonjour")
        assert result == "Bonjour"

    def test_omitted_closing_tag_detects_unclosed(self):
        extractor = TranslationExtractor("<TRANSLATION>", "</TRANSLATION>")
        assert extractor.omitted_closing_tag("<TRANSLATION>Bonjour") is True
        assert extractor.omitted_closing_tag("<TRANSLATION>Bonjour</TRANSLATION>") is False
        assert extractor.omitted_closing_tag("no tags here") is False

    def test_fuzzy_closing_tag(self):
        """Gemini-style typo in closing tag (</TRANATION>)"""
        extractor = TranslationExtractor("<TRANSLATION>", "</TRANSLATION>")
        result = extractor.extract("<TRANSLATION>Hello</TRANATION>")
        assert result == "Hello"
