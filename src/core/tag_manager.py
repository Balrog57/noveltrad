"""
Gestionnaire de balises (Tags) pour NovelTrad.
Extrait, protège et réinsère les balises de formatage HTML/XML dans les segments.
Conforme au cahier des charges §13.2.
"""
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TagError:
    """Represents a tag validation error."""
    tag: str
    error_type: str  # 'missing', 'extra', 'modified'
    message: str


@dataclass
class TagInfo:
    """Stores information about an extracted tag."""
    original: str       # Original tag text, e.g. '<b>'
    placeholder: str    # Placeholder, e.g. '<b0>'
    tag_type: str       # 'opening', 'closing', 'self_closing'
    tag_name: str       # e.g. 'b', 'i', 'a'
    position: int       # Position in the original text


# Pattern to match HTML/XML tags
TAG_PATTERN = re.compile(
    r'<(/?)(\w+)([^>]*)(/?)>',
    re.DOTALL
)

# Inline formatting tags that should be protected during translation
INLINE_TAGS = {
    'b', 'strong', 'i', 'em', 'u', 'a', 'span',
    'sub', 'sup', 'mark', 'small', 'del', 'ins',
    'code', 'abbr', 'ruby', 'rt', 'rp',
}


class TagManager:
    """
    Manages extraction, protection, and reinsertion of formatting tags
    during the translation process.

    Usage:
        tm = TagManager()
        clean_text, tags_map = tm.extract_tags("This is <b>bold</b> text.")
        # clean_text = "This is <b0>bold</b0> text."
        # After translation of clean_text:
        translated = tm.restore_tags(translated_clean, tags_map)
        errors = tm.validate_tags(source, translated)
    """

    def __init__(self, tag_format='numbered'):
        """
        Args:
            tag_format: 'numbered' for <b0>, <i1> style placeholders.
        """
        self.tag_format = tag_format

    def extract_tags(self, text):
        """
        Extract HTML/XML tags from text and replace with numbered placeholders.

        Args:
            text: Text containing HTML/XML tags.

        Returns:
            tuple: (clean_text, tags_map)
                - clean_text: Text with tags replaced by placeholders.
                - tags_map: dict mapping placeholder -> original tag.
        """
        if not text:
            return ('', {})

        tags_map = {}
        counter = {}

        def replace_tag(match):
            full_tag = match.group(0)
            is_closing = match.group(1) == '/'
            tag_name = match.group(2).lower()
            is_self_closing = match.group(4) == '/'

            # Only process known inline tags
            if tag_name not in INLINE_TAGS:
                return full_tag

            # Create numbered placeholder
            if tag_name not in counter:
                counter[tag_name] = 0

            if is_closing:
                # Use the previous index for the closing tag
                # (assuming well-formed XML/HTML where closing matches last opened)
                # Ensure we don't go below 0
                idx = max(0, counter[tag_name] - 1)
                placeholder = f'</{tag_name}{idx}>'
            elif is_self_closing:
                idx = counter[tag_name]
                placeholder = f'<{tag_name}{idx}/>'
                counter[tag_name] += 1
            else:
                idx = counter[tag_name]
                placeholder = f'<{tag_name}{idx}>'
                counter[tag_name] += 1

            tags_map[placeholder] = full_tag
            return placeholder

        clean_text = TAG_PATTERN.sub(replace_tag, text)
        return (clean_text, tags_map)

    def restore_tags(self, translated_text, tags_map):
        """
        Restore original tags from placeholders in translated text.

        Args:
            translated_text: Translated text containing placeholders.
            tags_map: dict mapping placeholder -> original tag.

        Returns:
            str: Text with original tags restored.
        """
        if not translated_text or not tags_map:
            return translated_text or ''

        result = translated_text
        for placeholder, original in tags_map.items():
            result = result.replace(placeholder, original)

        return result

    def validate_tags(self, source_text, target_text):
        """
        Validate that target text contains the same tags as source text.

        Args:
            source_text: Original source text with tags.
            target_text: Translated text that should contain the same tags.

        Returns:
            list[TagError]: List of tag validation errors (empty = valid).
        """
        if not source_text or not target_text:
            return []

        source_tags = self._extract_tag_list(source_text)
        target_tags = self._extract_tag_list(target_text)

        errors = []

        # Check for missing tags (in source but not in target)
        source_set = {}
        for tag in source_tags:
            source_set[tag] = source_set.get(tag, 0) + 1

        target_set = {}
        for tag in target_tags:
            target_set[tag] = target_set.get(tag, 0) + 1

        for tag, count in source_set.items():
            target_count = target_set.get(tag, 0)
            if target_count < count:
                errors.append(TagError(
                    tag=tag,
                    error_type='missing',
                    message=f"Tag '{tag}' is missing in the target text "
                            f"(expected {count}, found {target_count})."
                ))

        # Check for extra tags (in target but not in source)
        for tag, count in target_set.items():
            source_count = source_set.get(tag, 0)
            if count > source_count:
                errors.append(TagError(
                    tag=tag,
                    error_type='extra',
                    message=f"Extra tag '{tag}' found in target text "
                            f"(expected {source_count}, found {count})."
                ))

        return errors

    def _extract_tag_list(self, text):
        """Extract all inline tags from text as a list of strings."""
        tags = []
        for match in TAG_PATTERN.finditer(text):
            tag_name = match.group(2).lower()
            if tag_name in INLINE_TAGS:
                tags.append(match.group(0))
        return tags

    def strip_tags(self, text):
        """
        Remove all HTML/XML tags from text, leaving only the text content.

        Args:
            text: Text containing HTML tags.

        Returns:
            str: Plain text without tags.
        """
        if not text:
            return ''
        return re.sub(r'<[^>]+>', '', text)

    def count_tags(self, text):
        """
        Count the number of inline formatting tags in text.

        Args:
            text: Text to count tags in.

        Returns:
            int: Number of inline tags found.
        """
        if not text:
            return 0
        return len(self._extract_tag_list(text))
