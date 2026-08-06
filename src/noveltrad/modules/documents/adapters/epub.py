"""EPUB adapter (SDD 10.5, 10.6, 10.13).

Read with zipfile + lxml (strict). Only linear spine XHTML is extracted,
following the spine reading order. Archives are treated as untrusted: all
entries, internal references and manifest hrefs are validated before
writing a byte.
"""

from __future__ import annotations

import posixpath
import re
import zipfile
from pathlib import Path

from lxml import etree

from ..limits import (
    MAX_ARCHIVE_ENTRIES,
    MAX_MEMBER_BYTES,
    MAX_RATIO,
    MAX_TOTAL_DECOMPRESSED,
    MAX_XML_BYTES,
)
from .protocol import ConversionFailure, ConvertedDocument


class _ZipGuard:
    """Prevalidation of archive entries (10.6)."""

    def __init__(self, archive: zipfile.ZipFile) -> None:
        self._archive = archive
        self._by_name = {info.filename: info for info in archive.infolist()}
        self.entries = [info for info in archive.infolist() if not info.is_dir()]

    def validate(self) -> list[str]:
        """Return failure messages; empty when safe."""
        failures: list[str] = []
        total_uncompressed = 0
        total_compressed = 0
        if len(self.entries) > MAX_ARCHIVE_ENTRIES:
            failures.append("ARCHIVE_TOO_MANY_ENTRIES")
        seen: set[str] = set()
        for info in self.entries:
            name = info.filename
            normalized = name.strip("/")
            if (
                not name
                or "\x00" in name
                or "\\" in name
                or name.startswith("/")
                or normalized.startswith("..")
                or ".." in normalized.split("/")
            ):
                failures.append("ZIP_ESCAPE")
            if normalized in seen:
                failures.append("ZIP_COLLISION")
            seen.add(normalized)
            if info.file_size > MAX_MEMBER_BYTES:
                failures.append("ZIP_MEMBER_TOO_LARGE")
            if info.compress_size == 0 and info.file_size > 0:
                failures.append("ZIP_SUSPICIOUS_SIZE")
            if info.compress_size > 0 and info.file_size / info.compress_size > MAX_RATIO:
                failures.append("ZIP_HIGH_RATIO")
            total_uncompressed += info.file_size
            total_compressed += info.compress_size
            if total_uncompressed > MAX_TOTAL_DECOMPRESSED:
                failures.append("ZIP_TOTAL_TOO_LARGE")
        if total_compressed > 0 and total_uncompressed / total_compressed > MAX_RATIO:
            failures.append("ZIP_TOTAL_HIGH_RATIO")
        return failures

    def read(self, name: str) -> bytes:
        return self._archive.read(self._by_name[name])


def convert_epub(source_path: Path, work_dir: Path) -> ConvertedDocument | ConversionFailure:
    try:
        with zipfile.ZipFile(source_path) as archive:
            guard = _ZipGuard(archive)
            failures = guard.validate()
            if failures:
                return ConversionFailure(failures[0], "EPUB archive rejected: " + failures[0])
            return _extract_epub(archive, guard, source_path.stem, work_dir)
    except (zipfile.BadZipFile, OSError):
        return ConversionFailure("EPUB_BAD_ARCHIVE", "EPUB is not a valid zip archive")


def _extract_epub(
    archive: zipfile.ZipFile, guard: _ZipGuard, stem: str, work_dir: Path
) -> ConvertedDocument | ConversionFailure:
    del archive
    opf = _find_container(guard)
    if opf is None:
        return ConversionFailure("EPUB_NO_OPF", "EPUB container has no OPF manifest")
    spine_ids = _spine_order(guard, opf)
    if not spine_ids:
        return ConversionFailure("EPUB_NO_SPINE", "EPUB has no linear spine")
    items = _manifest_items(guard, opf)
    chapters: list[tuple[int, str | None]] = []
    markdown_parts: list[str] = []
    index = 0
    for idref in spine_ids:
        href = items.get(idref)
        if href is None:
            continue
        if href not in guard._by_name:
            continue
        payload = guard.read(href)
        if len(payload) > MAX_XML_BYTES:
            return ConversionFailure("EPUB_XML_TOO_LARGE", "EPUB XHTML member exceeds 64 Mio")
        text = _xhtml_to_markdown(payload)
        if text is None:
            return ConversionFailure("EPUB_XML_INVALID", "EPUB XHTML could not be parsed safely")
        title = _xhtml_title(payload)
        if text.strip():
            markdown_parts.append(text)
            chapters.append((index, title))
            index += 1
    if not markdown_parts:
        return ConversionFailure("EPUB_EMPTY", "EPUB contains no readable text")
    markdown = "\n\n".join(markdown_parts) + "\n"
    visible = _visible_text(markdown)
    return ConvertedDocument(
        display_name=stem,
        source_markdown=markdown,
        chapters=tuple(chapters),
        detected_language=None,
        word_count=len(visible.split()),
        character_count=len(visible.replace("\n", "")),
        images=(),
    )


def _find_container(guard: _ZipGuard) -> str | None:
    try:
        payload = guard.read("META-INF/container.xml")
    except KeyError:
        return None
    try:
        root = etree.fromstring(payload)
    except etree.XMLSyntaxError:
        return None
    for element in root.iter():
        if element.tag.endswith("rootfile"):
            full_path = element.get("full-path")
            if full_path and full_path in guard._by_name:
                return full_path
    return None


def _parse_opf(guard: _ZipGuard, opf_path: str):
    try:
        payload = guard.read(opf_path)
    except KeyError:
        return None
    parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)
    try:
        return etree.fromstring(payload, parser)
    except etree.XMLSyntaxError:
        return None


def _spine_order(guard: _ZipGuard, opf_path: str) -> list[str]:
    root = _parse_opf(guard, opf_path)
    if root is None:
        return []
    result: list[str] = []
    for element in root.iter():
        if element.tag.endswith("itemref"):
            idref = element.get("idref")
            if idref:
                result.append(idref)
    return result


def _manifest_items(guard: _ZipGuard, opf_path: str) -> dict[str, str]:
    root = _parse_opf(guard, opf_path)
    if root is None:
        return {}
    base = opf_path.rsplit("/", 1)[0] if "/" in opf_path else ""
    items: dict[str, str] = {}
    for element in root.iter():
        if element.tag.endswith("item"):
            item_id = element.get("id")
            href = element.get("href")
            media = element.get("media-type") or ""
            if item_id and href and media in ("application/xhtml+xml", "text/html"):
                resolved = _resolve_href(href, base)
                if resolved is not None:
                    items[item_id] = resolved
    return items


def _resolve_href(href: str, base: str) -> str | None:
    href = href.split("#")[0].strip()
    if not href or "\\" in href:
        return None
    resolved = posixpath.normpath(posixpath.join(base, href))
    if resolved.startswith("../") or resolved.startswith("/") or ".." in resolved.split("/"):
        return None
    return resolved


def _xhtml_to_markdown(payload: bytes) -> str | None:
    parser = etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        load_dtd=False,
        recover=False,
        huge_tree=False,
    )
    try:
        root = etree.fromstring(payload, parser)
    except etree.XMLSyntaxError:
        return None
    return _element_to_markdown(root)


def _element_to_markdown(element) -> str:
    parts: list[str] = []
    for node in element.iter():
        tag = _local(node.tag)
        if tag in (
            "script",
            "style",
            "iframe",
            "object",
            "embed",
            "head",
            "title",
            "meta",
            "link",
        ):
            continue
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            text = _node_text(node)
            if text.strip():
                parts.append(f"{'#' * int(tag[1])} {text.strip()}")
        elif tag in ("p", "div"):
            text = _node_text(node)
            if text.strip():
                parts.append(text.strip())
        elif tag == "li":
            text = _node_text(node)
            if text.strip():
                parts.append(f"- {text.strip()}")
        elif tag == "blockquote":
            text = _node_text(node)
            if text.strip():
                parts.append(f"> {text.strip()}")
        elif tag == "img":
            src = node.get("src") or ""
            alt = (node.get("alt") or "").strip()
            if src.startswith("data:image"):
                parts.append(f"![{alt}]({src})")
            elif alt:
                parts.append(alt)
        elif tag == "a":
            href = node.get("href") or ""
            text = _node_text(node).strip()
            if href.startswith(("http://", "https://")):
                parts.append(f"[{text}]({href})")
            elif text:
                parts.append(text)
    return "\n\n".join(parts)


def _node_text(node) -> str:
    text = "".join(node.itertext())
    return re.sub(r"\s+", " ", text).strip()


def _local(tag: str) -> str:
    if tag.startswith("{"):
        return tag.split("}", 1)[1]
    return tag


def _xhtml_title(payload: bytes) -> str | None:
    """Return the first heading text, or the document title as fallback."""
    try:
        root = etree.fromstring(payload)
    except etree.XMLSyntaxError:
        return None
    heading_text: str | None = None
    title_text: str | None = None
    for node in root.iter():
        tag = _local(node.tag)
        text = _node_text(node)
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6") and heading_text is None:
            heading_text = text or None
        if tag == "title" and title_text is None:
            title_text = text or None
    return heading_text or title_text


def _visible_text(markdown: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", markdown)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.M)
    text = re.sub(r"^\s*-\s+", "", text, flags=re.M)
    text = re.sub(r"^\s*>\s?", "", text, flags=re.M)
    return text
