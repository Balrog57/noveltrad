"""Assembler agent — Agent 9 (last stage) of the v4 pipeline.

Reconstructs the target document from the polished chunks. Supports
EPUB, DOCX, TXT, and SRT. The output path is provided in the task
payload (under `output_path`); the orchestrator also sets it in the
project context.

The assembler only acts on the FINAL `done` for the project. It
collects all polished chunks in the project, sorts them by chapter
then chunk_index, and writes them out.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .base_worker import BaseWorker

logger = logging.getLogger(__name__)


class Worker(BaseWorker):
    use_control_thread = True

    def handle_task(self, msg: dict[str, Any]) -> dict[str, Any] | None:
        action = msg.get("action")
        if action not in ("assemble",):
            return self._emit_error(
                msg.get("chunk_id"),
                "unknown_action",
                f"assembler: unknown action {action!r}",
            )
        payload = msg.get("payload") or {}
        chunk_id = msg.get("chunk_id")
        # The assembler task carries a snapshot of the project state.
        chunks: list[dict[str, Any]] = payload.get("chunks") or []
        output_path = payload.get("output_path")
        fmt = (payload.get("format") or "txt").lower()
        if not output_path:
            return self._emit_error(
                chunk_id, "missing_output_path", "assembler: output_path required"
            )
        out = Path(str(output_path))
        out.parent.mkdir(parents=True, exist_ok=True)
        try:
            if fmt == "epub":
                _write_epub(out, chunks, title=payload.get("title", out.stem))
            elif fmt == "docx":
                _write_docx(out, chunks)
            elif fmt == "srt":
                _write_srt(out, chunks)
            else:
                _write_txt(out, chunks)
        except Exception as exc:
            logger.exception("assembler: write failed")
            return self._emit_error(chunk_id, "write_failed", str(exc))
        return self._emit_done(
            chunk_id,
            {
                "output_path": str(out),
                "chunk_count": len(chunks),
                "status": "assembled",
            },
        )


def _sorted_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def key(c: dict[str, Any]) -> tuple[str, int]:
        return (str(c.get("chapter_id") or ""), int(c.get("chunk_index") or 0))

    return sorted(chunks, key=key)


def _polished_text(c: dict[str, Any]) -> str:
    return (
        c.get("polished_translation")
        or c.get("grammar_checked")
        or c.get("qa_checked")
        or c.get("glossary_applied")
        or c.get("raw_translation")
        or ""
    )


def _write_txt(path: Path, chunks: list[dict[str, Any]]) -> None:
    lines: list[str] = []
    for c in _sorted_chunks(chunks):
        title = c.get("chapter_title") or c.get("chapter_id") or ""
        if title and (not lines or lines[-1] != title):
            lines.append(f"## {title}")
            lines.append("")
        lines.append(_polished_text(c))
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_epub(path: Path, chunks: list[dict[str, Any]], title: str) -> None:
    try:
        from ebooklib import epub
    except ImportError as exc:
        raise RuntimeError("EPUB assembly requires EbookLib") from exc
    book = epub.EpubBook()
    book.set_identifier("noveltrad-assembled")
    book.set_title(title)
    book.set_language("en")
    chapters: list[Any] = []
    current_chap_title: str | None = None
    current_paragraphs: list[str] = []
    chapter_index = 0

    def _flush() -> None:
        nonlocal chapter_index, current_paragraphs, current_chap_title
        if not current_paragraphs:
            return
        chapter_index += 1
        c = epub.EpubHtml(
            title=current_chap_title or f"Chapter {chapter_index}",
            file_name=f"chap_{chapter_index:04d}.xhtml",
            lang="en",
        )
        body = "".join(f"<p>{p}</p>" for p in current_paragraphs if p.strip())
        c.content = (
            f"<html><head><title>{current_chap_title or ''}</title></head>"
            f"<body><h1>{current_chap_title or ''}</h1>{body}</body></html>"
        )
        book.add_item(c)
        chapters.append(c)
        current_paragraphs = []

    for c in _sorted_chunks(chunks):
        title_c = c.get("chapter_title") or c.get("chapter_id") or ""
        if current_chap_title is None:
            current_chap_title = title_c
        if title_c and title_c != current_chap_title:
            _flush()
            current_chap_title = title_c
        current_paragraphs.append(_polished_text(c))
    _flush()
    book.toc = tuple(chapters)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", *chapters]
    epub.write_epub(str(path), book)


def _write_docx(path: Path, chunks: list[dict[str, Any]]) -> None:
    try:
        import docx
    except ImportError as exc:
        raise RuntimeError("DOCX assembly requires python-docx") from exc
    doc = docx.Document()
    current_chap: str | None = None
    for c in _sorted_chunks(chunks):
        title = c.get("chapter_title") or c.get("chapter_id") or ""
        if title and title != current_chap:
            doc.add_heading(title, level=1)
            current_chap = title
        text = _polished_text(c)
        if text:
            doc.add_paragraph(text)
    doc.save(str(path))


_SRT_TIME = "%H:%M:%S,%f"


def _write_srt(path: Path, chunks: list[dict[str, Any]]) -> None:
    out: list[str] = []
    index = 1
    start = 0
    for c in _sorted_chunks(chunks):
        text = _polished_text(c).strip()
        if not text:
            continue
        # Rough heuristic: 3 sec per chunk, 12 chars/sec reading speed.
        import datetime as _dt

        s = _dt.datetime.utcfromtimestamp(start)
        end_ts = start + max(3, len(text) // 12)
        e = _dt.datetime.utcfromtimestamp(end_ts)
        out.append(str(index))
        out.append(
            f"{s.strftime(_SRT_TIME)[:-3]} --> {e.strftime(_SRT_TIME)[:-3]}"
        )
        out.append(text)
        out.append("")
        index += 1
        start = end_ts + 1
    path.write_text("\n".join(out), encoding="utf-8")


__all__ = ["Worker"]
