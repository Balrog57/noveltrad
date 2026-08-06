"""DOCX adapter (SDD 10.5, 10.13).

DOCX is an untrusted zip archive: entries are prevalidated, then mammoth
extracts semantic content (body, headings, paragraphs, lists, tables,
HTTP(S) links, footnotes exposed by mammoth, inline images).
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

import mammoth

from .epub import _ZipGuard
from .protocol import ConversionFailure, ConvertedDocument


def convert_docx(source_path: Path, work_dir: Path) -> ConvertedDocument | ConversionFailure:
    del work_dir
    try:
        with zipfile.ZipFile(source_path) as archive:
            guard = _ZipGuard(archive)
            failures = guard.validate()
            if failures:
                return ConversionFailure(failures[0], "DOCX archive rejected: " + failures[0])
            return _extract_docx(source_path, source_path.stem)
    except (zipfile.BadZipFile, OSError):
        return ConversionFailure("DOCX_BAD_ARCHIVE", "DOCX is not a valid zip archive")


def _extract_docx(source_path: Path, stem: str) -> ConvertedDocument | ConversionFailure:
    try:
        result = mammoth.convert_to_markdown(source_path)
        markdown = result.value.strip()
    except Exception:  # noqa: BLE001 - mammoth raises generic errors
        return ConversionFailure("DOCX_EXTRACT_FAILED", "DOCX extraction failed")
    if not markdown:
        return ConversionFailure("DOCX_EMPTY", "DOCX contains no readable text")
    markdown = _sanitize_markdown(markdown)
    title = _first_heading(markdown)
    visible = _visible(markdown)
    return ConvertedDocument(
        display_name=stem,
        source_markdown=markdown,
        chapters=((0, title),),
        detected_language=None,
        word_count=len(visible.split()),
        character_count=len(visible.replace("\n", "")),
        images=(),
    )


def _sanitize_markdown(markdown: str) -> str:
    """Remove scripts/styles and non-HTTP(S) links mammoth may emit."""
    markdown = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", "", markdown)
    return markdown


def _first_heading(markdown: str) -> str | None:
    for line in markdown.splitlines():
        match = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
        if match:
            return match.group(2).strip()
    return None


def _visible(markdown: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", markdown)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.M)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.M)
    text = re.sub(r"^\s*\|\s*", "", text, flags=re.M)
    text = re.sub(r"\|", " ", text)
    return text
