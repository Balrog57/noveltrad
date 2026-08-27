"""HTML tag classification and priority detection.

This module provides utilities for classifying HTML tags by type and
determining split priorities for HTML-aware chunking.
"""
import re

# Pre-compiled once: HtmlChunker calls these classifiers for every placeholder
# pair in a chapter. Extracting the tag name once and doing an O(1) set lookup
# replaces the previous O(|BLOCK_TAGS|) substring scan per call.
_CLOSING_TAG_NAME_RE = re.compile(r"</(\w+)", re.IGNORECASE)
_OPENING_TAG_NAME_RE = re.compile(r"<(?!/)(\w+)", re.IGNORECASE)


def _closing_tag_name(tag: str) -> str | None:
    match = _CLOSING_TAG_NAME_RE.search(tag)
    return match.group(1).lower() if match else None


def _opening_tag_name(tag: str) -> str | None:
    match = _OPENING_TAG_NAME_RE.search(tag)
    return match.group(1).lower() if match else None


class TagClassifier:
    """Classifies HTML tags by type and determines split priorities.

    This class provides methods to identify block-level tags, determine
    split priorities for chunking, and detect chapter headings.
    """

    BLOCK_TAGS = {'p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                  'blockquote', 'section', 'article', 'li', 'tr', 'td', 'th'}

    CHAPTER_HEADINGS = {'h1', 'h2', 'h3'}
    MAJOR_SECTIONS = {'h4', 'h5', 'h6', 'section', 'article'}
    PARAGRAPHS = {'p', 'div', 'blockquote'}

    def get_split_priority(self, tag: str) -> int:
        """Get priority for splitting at this tag.

        Lower number = higher priority (preferred split point).

        Priority levels:
        1: Chapter headings (h1, h2, h3)
        2: Major sections (h4, h5, h6, section, article)
        3: Paragraphs and divs (p, div, blockquote)
        4: Other blocks (li, tr, td, th)

        Args:
            tag: HTML tag string (e.g., "</p>", "<div>")

        Returns:
            Priority level (1-4)
        """
        tag_name = _closing_tag_name(tag)
        if tag_name is None:
            return 4

        if tag_name in self.CHAPTER_HEADINGS:
            return 1
        if tag_name in self.MAJOR_SECTIONS:
            return 2
        if tag_name in self.PARAGRAPHS:
            return 3
        return 4

    def is_block_closing_tag(self, tag: str) -> bool:
        """Check if tag is a block closing tag.

        Examples: "</p>", "</div>", "</h1>"

        Args:
            tag: HTML tag string

        Returns:
            True if tag is a block closing tag
        """
        tag_name = _closing_tag_name(tag)
        return tag_name is not None and tag_name in self.BLOCK_TAGS

    def is_block_opening_tag(self, tag: str) -> bool:
        """Check if tag is a block opening tag.

        Examples: "<p>", "<div>", "<h1 class='title'>"

        Args:
            tag: HTML tag string

        Returns:
            True if tag is a block opening tag
        """
        tag_name = _opening_tag_name(tag)
        return tag_name is not None and tag_name in self.BLOCK_TAGS

    def is_chapter_heading(self, tag: str) -> bool:
        """Check if tag is a chapter heading (h1-h3).

        Chapter headings are high-priority split points as they typically
        mark major structural boundaries in EPUB content.

        Args:
            tag: HTML tag string

        Returns:
            True if tag is a chapter heading
        """
        tag_name = _closing_tag_name(tag)
        return tag_name is not None and tag_name in self.CHAPTER_HEADINGS
