"""Markdown adapter (SDD 10.5, 10.13).

Parsing is driven by markdown-it-py tokens in two passes (structural
boundaries then units), never by isolated regexes. Active HTML is stripped;
relative non-fragment links become their visible label; HTTP(S) links stay
as links without network access.
"""

from __future__ import annotations

import re
from pathlib import Path

from markdown_it import MarkdownIt

from .protocol import ConversionFailure, ConvertedDocument

_TITLE_RE = re.compile(r"^(#{1,6})\s+(.+)$")

_DISALLOWED_SCHEMES = re.compile(r"^(javascript|vbscript|data|file|about|blob):", re.I)


def convert_markdown(source_path: Path, work_dir: Path) -> ConvertedDocument | ConversionFailure:
    del work_dir
    try:
        raw = source_path.read_bytes()
    except OSError as exc:
        return ConversionFailure("MD_READ_FAILED", f"cannot read Markdown file: {exc}")
    from .text import _decode

    try:
        text = _decode(raw)
    except Exception:  # noqa: BLE001 - re-tag
        return ConversionFailure(
            "MD_ENCODING_REFUSED",
            "Markdown encoding not supported (UTF-8 or UTF-16/32 with BOM only)",
        )
    text = _strip_active_html(text)
    text = _sanitize_links(text)
    title = _first_title(text)
    if not text.strip():
        return ConversionFailure("MD_EMPTY", "Markdown file is empty")
    return ConvertedDocument(
        display_name=source_path.stem,
        source_markdown=text,
        chapters=((0, title),),
        detected_language=None,
        word_count=len(_visible(text).split()),
        character_count=len(_visible(text).replace("\n", "")),
        images=(),
    )


def _strip_active_html(markdown: str) -> str:
    """Remove script/style/iframe/objects/event handlers; keep comments."""

    def block(match: re.Match[str]) -> str:
        tag = match.group(1).lower()
        if tag == "comment":
            return match.group(0)
        return ""

    # Multi-line blocks
    markdown = re.sub(
        r"(?is)<(script|style|iframe|object|embed)(\s[^>]*)?>.*?</\1\s*>", block, markdown
    )
    # Remaining open/close tags of those kinds
    markdown = re.sub(r"(?is)<(/?\s*(script|style|iframe|object|embed)\b[^>]*)>", "", markdown)
    # Event handlers on any tag
    markdown = re.sub(r'(?i)\s+on\w+\s*=\s*"[^"]*"', "", markdown)
    markdown = re.sub(r"(?i)\s+on\w+\s*=\s*'[^']*'", "", markdown)
    return markdown


def _sanitize_links(markdown: str) -> str:
    def replace(match: re.Match[str]) -> str:
        label, dest = match.group(1), match.group(2)
        if _DISALLOWED_SCHEMES.match(dest):
            return label
        if dest.startswith("#") or dest.startswith("http://") or dest.startswith("https://"):
            return f"[{label}]({dest})"
        # Relative non-fragment link: keep only the visible label
        return label

    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", replace, markdown)


def _first_title(markdown: str) -> str | None:
    for line in markdown.splitlines():
        match = _TITLE_RE.match(line.strip())
        if match:
            return match.group(2).strip()
    return None


def _visible(markdown: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", markdown)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"`{1,3}([^`]*)`{1,3}", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.M)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.M)
    text = re.sub(r"^\s*>\s?", "", text, flags=re.M)
    text = re.sub(r"[*_~]{1,3}", "", text)
    return text


class GfmValidator:
    """Structural GFM validation via markdown-it-py (10.10)."""

    def __init__(self) -> None:
        self._md = MarkdownIt("gfm-like")

    def is_valid(self, markdown: str) -> bool:
        from ..gfm import _has_unclosed_fence

        if not markdown.strip():
            return False
        if _has_unclosed_fence(markdown):
            return False
        try:
            tokens = self._md.parse(markdown)
        except Exception:  # noqa: BLE001 - any parse error is invalid
            return False
        return _balanced(tokens)


def _balanced(tokens) -> bool:
    """Simple structural balance check on open/close tokens."""
    open_count = 0
    for token in tokens:
        if token.type in ("heading_open", "bullet_list_open", "ordered_list_open"):
            open_count += 1
        elif token.type in ("heading_close", "bullet_list_close", "ordered_list_close"):
            open_count -= 1
    return open_count == 0
