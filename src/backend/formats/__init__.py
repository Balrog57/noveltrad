"""File format handlers — extract structured chunks from input files.

Each handler exposes a common surface:

    Handler.from_path(path) -> Document
    Document.title, .author
    Document.chapters: list[Chapter]
    Chapter.id, .title, .paragraphs: list[str]

Chunking rules (shared with the Parser agent):
  * Paragraphs < MIN_CHARS are merged with the next one to avoid
    under-sized chunks.
  * Paragraphs > MAX_CHARS are split on sentence boundaries.
  * Resulting chunks are roughly MIN_CHARS..MAX_CHARS long.

This module is GUI-free and PyQt6-free. It can be imported from the
FastAPI process and from the Parser subprocess.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

logger = logging.getLogger(__name__)


MIN_CHARS = 200
MAX_CHARS = 800
SOFT_TARGET = 500


@dataclass
class Chapter:
    id: str
    title: str
    paragraphs: list[str] = field(default_factory=list)

    def plain_text(self) -> str:
        return "\n\n".join(p for p in self.paragraphs if p)


@dataclass
class Document:
    title: str
    author: str
    chapters: list[Chapter] = field(default_factory=list)
    source_format: str = "unknown"
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------- chunking ----------


def chunk_paragraphs(
    paragraphs: Iterable[str],
    chapter_id: str,
    chapter_title: str,
    min_chars: int = MIN_CHARS,
    max_chars: int = MAX_CHARS,
    soft_target: int = SOFT_TARGET,
) -> list[dict[str, Any]]:
    """Group paragraphs into chunks of roughly soft_target characters.

    The output list contains dicts with: id, chapter_id, chapter_title,
    chunk_index, source_text, source_hash. `id` is a deterministic
    sha1-based hash so re-parsing yields stable IDs (resumability).
    """
    import hashlib
    import uuid

    merged: list[str] = []
    buf = ""
    for p in paragraphs:
        p = (p or "").strip()
        if not p:
            continue
        if not buf:
            buf = p
            continue
        if len(buf) < min_chars:
            buf = f"{buf}\n\n{p}"
        else:
            merged.append(buf)
            buf = p
    if buf:
        merged.append(buf)

    out: list[dict[str, Any]] = []
    for idx, text in enumerate(merged):
        for sub in _split_oversize(text, max_chars):
            chunk_id = _stable_chunk_id(chapter_id, idx, sub)
            out.append(
                {
                    "id": chunk_id,
                    "chapter_id": chapter_id,
                    "chapter_title": chapter_title,
                    "chunk_index": idx,
                    "source_text": sub,
                    "source_hash": hashlib.sha256(sub.encode("utf-8")).hexdigest(),
                }
            )
    return out


def _split_oversize(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    parts: list[str] = []
    cursor = 0
    while cursor < len(text):
        if cursor + max_chars >= len(text):
            parts.append(text[cursor:].strip())
            break
        window = text[cursor : cursor + max_chars]
        cut = _find_sentence_break(window)
        if cut is None or cut < max_chars // 2:
            cut = max_chars
        parts.append(text[cursor : cursor + cut].strip())
        cursor += cut
    return [p for p in parts if p]


_SENTENCE_END = re.compile(r"[.!?。!?][\"')\]]?\s")


def _find_sentence_break(window: str) -> int | None:
    last = None
    for m in _SENTENCE_END.finditer(window):
        last = m.end()
    return last


def _stable_chunk_id(chapter_id: str, idx: int, text: str) -> str:
    import hashlib

    h = hashlib.sha1(f"{chapter_id}::{idx}::{text}".encode("utf-8")).hexdigest()
    return h[:16]


# ---------- format-specific extractors ----------


def _read_epub(path: Path) -> Document:
    try:
        import ebooklib
        from ebooklib import epub
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise RuntimeError(
            "EPUB support requires EbookLib and BeautifulSoup4"
        ) from exc

    book = epub.read_epub(str(path), options={"ignore_ncx": True})
    title = _safe_meta(book, "title") or path.stem
    author = _safe_meta(book, "creator") or _safe_meta(book, "author") or ""
    chapters: list[Chapter] = []
    spine_ids = list(book.spine)
    for i, spine_ref in enumerate(spine_ids):
        item_id, _ = spine_ref
        item = book.get_item_with_id(item_id)
        if item is None or item.get_type() != ebooklib.ITEM_DOCUMENT:
            continue
        soup = BeautifulSoup(item.get_content(), "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = soup.get_text(separator="\n")
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        if not paragraphs:
            continue
        chap_title = _first_meaningful_line(paragraphs) or f"Chapter {i + 1}"
        chapters.append(
            Chapter(id=f"ch{i + 1:04d}", title=chap_title, paragraphs=paragraphs)
        )
    return Document(
        title=title,
        author=author,
        chapters=chapters,
        source_format="epub",
        metadata={"path": str(path)},
    )


def _safe_meta(book: Any, key: str) -> str | None:
    try:
        data = book.get_metadata("DC", key)
        if not data:
            return None
        return str(data[0][0]) if data else None
    except Exception:
        return None


def _first_meaningful_line(paragraphs: list[str]) -> str | None:
    for p in paragraphs[:3]:
        if 3 <= len(p) <= 120 and not p.endswith("."):
            return p
    return None


def _read_docx(path: Path) -> Document:
    try:
        import docx
    except ImportError as exc:
        raise RuntimeError("DOCX support requires python-docx") from exc

    doc = docx.Document(str(path))
    title = doc.core_properties.title or path.stem
    author = doc.core_properties.author or ""
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]
    chapters = [
        Chapter(
            id="ch0001",
            title=title or "Document",
            paragraphs=paragraphs,
        )
    ]
    return Document(
        title=title,
        author=author,
        chapters=chapters,
        source_format="docx",
        metadata={"path": str(path)},
    )


def _read_txt(path: Path) -> Document:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = [ln.rstrip() for ln in text.splitlines()]
    paragraphs: list[str] = []
    buf: list[str] = []
    for ln in lines:
        if not ln.strip():
            if buf:
                paragraphs.append(" ".join(buf).strip())
                buf = []
            continue
        buf.append(ln.strip())
    if buf:
        paragraphs.append(" ".join(buf).strip())

    chapters: list[Chapter] = []
    current: Chapter | None = None
    heading_re = re.compile(r"^(chapter|chapitre|第[0-9一二三四五六七八九十百]+章)\b", re.I)
    for idx, p in enumerate(paragraphs):
        if heading_re.match(p) and len(p) < 120:
            if current is not None:
                chapters.append(current)
            current = Chapter(
                id=f"ch{len(chapters) + 1:04d}",
                title=p,
                paragraphs=[],
            )
        else:
            if current is None:
                current = Chapter(
                    id="ch0001",
                    title=path.stem,
                    paragraphs=[],
                )
            current.paragraphs.append(p)
    if current is not None:
        chapters.append(current)
    if not chapters:
        chapters.append(Chapter(id="ch0001", title=path.stem, paragraphs=paragraphs))
    return Document(
        title=path.stem,
        author="",
        chapters=chapters,
        source_format="txt",
        metadata={"path": str(path)},
    )


_SRT_TIME = re.compile(
    r"(\d{2}):(\d{2}):(\d{2})[,\.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,\.](\d{3})"
)


def _read_srt(path: Path) -> Document:
    text = path.read_text(encoding="utf-8", errors="replace")
    blocks = re.split(r"\n\s*\n", text.strip())
    paragraphs: list[str] = []
    for block in blocks:
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        if lines[0].isdigit():
            lines = lines[1:]
        if not lines:
            continue
        m = _SRT_TIME.match(lines[0]) if lines else None
        if m:
            lines = lines[1:]
        paragraphs.append(" ".join(lines))
    return Document(
        title=path.stem,
        author="",
        chapters=[Chapter(id="ch0001", title=path.stem, paragraphs=paragraphs)],
        source_format="srt",
        metadata={"path": str(path)},
    )


_READERS = {
    ".epub": _read_epub,
    ".docx": _read_docx,
    ".txt": _read_txt,
    ".srt": _read_srt,
}


def detect_format(path: str | Path) -> str:
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix in _READERS:
        return suffix.lstrip(".")
    raise ValueError(f"Unsupported file format: {suffix!r}")


def read_document(path: str | Path) -> Document:
    p = Path(path)
    suffix = p.suffix.lower()
    reader = _READERS.get(suffix)
    if reader is None:
        raise ValueError(f"Unsupported file format: {suffix!r}")
    return reader(p)


__all__ = [
    "Chapter",
    "Document",
    "chunk_paragraphs",
    "detect_format",
    "read_document",
    "MIN_CHARS",
    "MAX_CHARS",
    "SOFT_TARGET",
]
