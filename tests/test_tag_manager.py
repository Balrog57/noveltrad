"""Tests for the TagManager module."""
import pytest
from src.core.tag_manager import TagManager, TagError


@pytest.fixture
def tm():
    return TagManager()


class TestExtractTags:
    """Test tag extraction and placeholder creation."""

    def test_simple_bold(self, tm):
        text = "This is <b>bold</b> text."
        clean, tags_map = tm.extract_tags(text)
        assert '<b>' not in clean or '<b0>' in clean
        assert len(tags_map) > 0

    def test_multiple_tags(self, tm):
        text = "This is <b>bold</b> and <i>italic</i> text."
        clean, tags_map = tm.extract_tags(text)
        assert len(tags_map) == 4  # <b>, </b>, <i>, </i>

    def test_nested_tags(self, tm):
        text = "This is <b><i>bold italic</i></b> text."
        clean, tags_map = tm.extract_tags(text)
        assert len(tags_map) == 4

    def test_no_tags(self, tm):
        text = "Plain text without any tags."
        clean, tags_map = tm.extract_tags(text)
        assert clean == text
        assert tags_map == {}

    def test_empty_text(self, tm):
        clean, tags_map = tm.extract_tags("")
        assert clean == ''
        assert tags_map == {}

    def test_none_text(self, tm):
        clean, tags_map = tm.extract_tags(None)
        assert clean == ''
        assert tags_map == {}

    def test_non_inline_tags_preserved(self, tm):
        text = "<div>This is a <b>bold</b> div.</div>"
        clean, tags_map = tm.extract_tags(text)
        # <div> and </div> should remain as-is (not inline tags)
        assert '<div>' in clean
        assert '</div>' in clean

    def test_tag_with_attributes(self, tm):
        text = 'Click <a href="url">here</a> please.'
        clean, tags_map = tm.extract_tags(text)
        assert len(tags_map) == 2  # <a> and </a>


class TestRestoreTags:
    """Test restoring original tags from placeholders."""

    def test_roundtrip(self, tm):
        original = "This is <b>bold</b> and <i>italic</i>."
        clean, tags_map = tm.extract_tags(original)
        restored = tm.restore_tags(clean, tags_map)
        assert restored == original

    def test_empty_map(self, tm):
        result = tm.restore_tags("Hello world.", {})
        assert result == "Hello world."

    def test_none_text(self, tm):
        result = tm.restore_tags(None, {})
        assert result == ''


class TestValidateTags:
    """Test tag validation between source and target."""

    def test_valid_tags(self, tm):
        source = "This is <b>bold</b> text."
        target = "Ceci est du texte <b>gras</b>."
        errors = tm.validate_tags(source, target)
        assert errors == []

    def test_missing_tag(self, tm):
        source = "This is <b>bold</b> text."
        target = "Ceci est du texte gras."
        errors = tm.validate_tags(source, target)
        assert len(errors) > 0
        assert any(e.error_type == 'missing' for e in errors)

    def test_extra_tag(self, tm):
        source = "This is plain text."
        target = "Ceci est du texte <b>gras</b>."
        errors = tm.validate_tags(source, target)
        assert len(errors) > 0
        assert any(e.error_type == 'extra' for e in errors)

    def test_empty_texts(self, tm):
        assert tm.validate_tags("", "") == []
        assert tm.validate_tags(None, None) == []


class TestStripTags:
    """Test tag stripping."""

    def test_strip_simple(self, tm):
        text = "This is <b>bold</b> text."
        result = tm.strip_tags(text)
        assert result == "This is bold text."

    def test_strip_nested(self, tm):
        text = "<p>Hello <b><i>world</i></b></p>"
        result = tm.strip_tags(text)
        assert result == "Hello world"

    def test_strip_empty(self, tm):
        assert tm.strip_tags("") == ''
        assert tm.strip_tags(None) == ''


class TestCountTags:
    """Test tag counting."""

    def test_count_simple(self, tm):
        text = "This is <b>bold</b> text."
        assert tm.count_tags(text) == 2

    def test_count_zero(self, tm):
        assert tm.count_tags("No tags here.") == 0

    def test_count_empty(self, tm):
        assert tm.count_tags("") == 0
        assert tm.count_tags(None) == 0
