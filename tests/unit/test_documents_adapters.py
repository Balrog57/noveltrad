"""Unit tests for import adapters (SDD 10.5, 10.13)."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

from noveltrad.modules.documents.adapters.epub import convert_epub
from noveltrad.modules.documents.adapters.markdown import GfmValidator, convert_markdown
from noveltrad.modules.documents.adapters.protocol import ConversionFailure
from noveltrad.modules.documents.adapters.srt import convert_srt
from noveltrad.modules.documents.adapters.text import convert_txt


def test_txt_conversion(tmp_path: Path):
    source = tmp_path / "novel.txt"
    source.write_bytes(b"Chapter one.\n\nIt was a dark night.\n")
    result = convert_txt(source, tmp_path)
    assert result.source_markdown.startswith("Chapter one.")
    assert result.word_count >= 7


def test_txt_refuses_latin1(tmp_path: Path):
    source = tmp_path / "latin.txt"
    source.write_bytes("caf\xe9".encode("latin-1"))
    result = convert_txt(source, tmp_path)
    assert isinstance(result, ConversionFailure)
    assert result.error_code == "TXT_ENCODING_REFUSED"


def test_markdown_conversion_strips_script(tmp_path: Path):
    source = tmp_path / "doc.md"
    source.write_text(
        "# Title\n\n<script>alert(1)</script>\n\n[link](javascript:alert(1)) plain\n\nbody text\n"
    )
    result = convert_markdown(source, tmp_path)
    assert "script" not in result.source_markdown
    assert "javascript:" not in result.source_markdown
    assert result.chapters == ((0, "Title"),)


def test_markdown_keeps_https_links(tmp_path: Path):
    source = tmp_path / "doc.md"
    source.write_text("See [docs](https://example.com).\n")
    result = convert_markdown(source, tmp_path)
    assert "https://example.com" in result.source_markdown


def test_srt_conversion(tmp_path: Path):
    source = tmp_path / "subs.srt"
    source.write_text(
        "1\n00:00:01,000 --> 00:00:03,000\nHello world\n\n"
        "2\n00:00:04,000 --> 00:00:06,000\nGoodbye\n",
        encoding="utf-8",
    )
    result = convert_srt(source, tmp_path)
    assert "noveltrad:srt-cue:1" in result.source_markdown
    assert "Hello world" in result.source_markdown


def test_gfm_validator():
    validator = GfmValidator()
    assert validator.is_valid("# Title\n\nSome *text* with **bold** and `code`.")
    assert not validator.is_valid("")
    assert not validator.is_valid("```python\ndef x(): pass")


def _make_epub(xhtml: list[tuple[str, str]]) -> Path:
    """Build a minimal EPUB: container + OPF with spine + one XHTML per item."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "META-INF/container.xml",
            '<?xml version="1.0"?><container><rootfiles>'
            '<rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>'
            "</rootfiles></container>",
        )
        items = []
        spines = []
        for index, (name, _) in enumerate(xhtml):
            items.append(f'<item id="ch{index}" href="{name}" media-type="application/xhtml+xml"/>')
            spines.append(f'<itemref idref="ch{index}"/>')
        archive.writestr(
            "OEBPS/content.opf",
            '<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf">'
            "<manifest>"
            + "".join(items)
            + "</manifest><spine>"
            + "".join(spines)
            + "</spine></package>",
        )
        for index, (name, body) in enumerate(xhtml):
            archive.writestr(
                f"OEBPS/{name}",
                '<?xml version="1.0"?><html xmlns="http://www.w3.org/1999/xhtml">'
                f"<head><title>Chapter {index}</title></head><body>{body}</body></html>",
            )
    return buffer.getvalue()


def _write_epub(tmp_path: Path, xhtml: list[tuple[str, str]]) -> Path:
    target = tmp_path / "book.epub"
    target.write_bytes(_make_epub(xhtml))
    return target


def test_epub_conversion(tmp_path: Path):
    epub = _write_epub(
        tmp_path,
        [
            ("ch1.xhtml", "<h1>One</h1><p>First paragraph.</p>"),
            ("ch2.xhtml", "<h2>Two</h2><p>Second paragraph.</p>"),
        ],
    )
    result = convert_epub(epub, tmp_path)
    assert "First paragraph." in result.source_markdown
    assert "Second paragraph." in result.source_markdown
    assert len(result.chapters) == 2
    assert result.chapters[1][1] == "Two"


def test_epub_zip_slip_rejected(tmp_path: Path):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("../escape.txt", "evil")
    evil = tmp_path / "evil.epub"
    evil.write_bytes(buffer.getvalue())
    result = convert_epub(evil, tmp_path)
    assert isinstance(result, ConversionFailure)
    assert "ZIP" in result.error_code


def test_epub_high_ratio_rejected(tmp_path: Path):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("META-INF/container.xml", "x" * 5000 + "</container>")
    bomb = tmp_path / "bomb.epub"
    bomb.write_bytes(buffer.getvalue())
    result = convert_epub(bomb, tmp_path)
    assert isinstance(result, ConversionFailure)
