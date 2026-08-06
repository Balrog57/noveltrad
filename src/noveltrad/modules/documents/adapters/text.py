"""TXT adapter (SDD 10.5, 10.13).

Accepts UTF-8 with or without BOM and UTF-16/UTF-32 with BOM only; any
other encoding is refused rather than guessed. Normalizes to UTF-8 LF.
"""

from __future__ import annotations

from pathlib import Path

from noveltrad.core.exceptions import ImportConversionError

from .protocol import ConversionFailure, ConvertedDocument

MAX_FILE_BYTES = 512 * 1024 * 1024


def _decode(raw: bytes) -> str:
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw[3:].decode("utf-8")
    if raw.startswith(b"\xff\xfe\x00\x00"):  # UTF-32LE BOM
        return raw[4:].decode("utf-32-le")
    if raw.startswith(b"\x00\x00\xfe\xff"):  # UTF-32BE BOM
        return raw[4:].decode("utf-32-be")
    if raw.startswith(b"\xff\xfe"):  # UTF-16LE BOM
        return raw[2:].decode("utf-16-le")
    if raw.startswith(b"\xfe\xff"):  # UTF-16BE BOM
        return raw[2:].decode("utf-16-be")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ImportConversionError(
            "TXT_ENCODING_REFUSED",
            "TXT encoding not supported (UTF-8 or UTF-16/32 with BOM only)",
        ) from exc


def convert_txt(source_path: Path, work_dir: Path) -> ConvertedDocument | ConversionFailure:
    del work_dir
    try:
        raw = source_path.read_bytes()
    except OSError as exc:
        return ConversionFailure("TXT_READ_FAILED", f"cannot read TXT file: {exc}")
    if len(raw) > MAX_FILE_BYTES:
        return ConversionFailure("TXT_TOO_LARGE", "TXT file exceeds 512 Mio")
    try:
        text = _decode(raw)
    except ImportConversionError as exc:
        return ConversionFailure(exc.error_code, exc.safe_message)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    markdown = "\n\n".join(paragraphs) + ("\n" if paragraphs else "")
    visible = _visible_text(markdown)
    return ConvertedDocument(
        display_name=source_path.stem,
        source_markdown=markdown,
        chapters=((0, None),),
        detected_language=None,
        word_count=len(visible.split()),
        character_count=len(visible),
        images=(),
    )


def _visible_text(markdown: str) -> str:
    return markdown
