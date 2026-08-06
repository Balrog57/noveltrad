"""Common import adapter contract (SDD 10.14).

Each adapter follows: inspect -> extract -> normalize -> protect -> validate
-> publish. The output is normalized GFM plus WebP files.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from noveltrad.core.contracts import LanguageCode


@dataclass(frozen=True, slots=True)
class ConvertedDocument:
    """Result of a successful conversion."""

    display_name: str
    source_markdown: str
    chapters: tuple[tuple[int, str | None], ...]  # (order_index, title)
    detected_language: LanguageCode | str | None
    word_count: int
    character_count: int
    images: tuple[str, ...]  # relative image paths under images/


@dataclass(frozen=True, slots=True)
class ConversionFailure:
    error_code: str
    safe_message: str


class FormatAdapter(Protocol):
    """Closed set of adapters: epub, docx, markdown, text, srt."""

    format_name: str

    def convert(self, source_path: Path, work_dir: Path) -> ConvertedDocument | ConversionFailure:
        """Convert a validated temporary file into GFM/WebP content."""
        ...
