"""SRT adapter (SDD 10.5).

Cues are preserved: order, text, index and timestamps encoded in protected
GFM comments `noveltrad:srt-cue`. Exact numbering/spacing/line endings are
abandoned; the SRT cannot be recreated identically.
"""

from __future__ import annotations

import re
from pathlib import Path

from .protocol import ConversionFailure, ConvertedDocument

_CUE_BLOCK = re.compile(
    r"(?ms)^(\d+)\s*\n(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*"
    r"(\d{2}:\d{2}:\d{2}[,.]\d{3})(.*?)(?=^\d+\s*\n\d{2}:\d{2}:\d{2}|\Z)"
)


def convert_srt(source_path: Path, work_dir: Path) -> ConvertedDocument | ConversionFailure:
    del work_dir
    try:
        raw = source_path.read_bytes()
    except OSError as exc:
        return ConversionFailure("SRT_READ_FAILED", f"cannot read SRT file: {exc}")
    from .text import _decode

    try:
        text = _decode(raw)
    except Exception:  # noqa: BLE001 - re-tag
        return ConversionFailure(
            "SRT_ENCODING_REFUSED", "SRT encoding not supported (UTF-8 or UTF-16/32 with BOM only)"
        )
    blocks: list[str] = []
    for match in _CUE_BLOCK.finditer(text):
        index = match.group(1)
        start = match.group(2).replace(",", ".")
        end = match.group(3).replace(",", ".")
        content = match.group(4).strip()
        marker = f"<!--noveltrad:srt-cue:{index}|{start}-->{end}-->"
        blocks.append(f"{marker}\n{content}")
    if not blocks:
        return ConversionFailure("SRT_PARSE_FAILED", "no valid SRT cues found")
    markdown = "\n\n".join(blocks) + "\n"
    visible = re.sub(r"<!--noveltrad:srt-cue:.*?-->", "", markdown)
    return ConvertedDocument(
        display_name=source_path.stem,
        source_markdown=markdown,
        chapters=((0, None),),
        detected_language=None,
        word_count=len(visible.split()),
        character_count=len(visible.replace("\n", "")),
        images=(),
    )
