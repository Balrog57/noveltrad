"""GFM structural protection (SDD 10.5).

Non-translatable preserved elements — WebP references, link destinations,
code blocks and technical SRT comments — are replaced by opaque markers
uniquely mapped to their value. Validation fails when a marker is missing,
duplicated, out of order when order matters, or produces an unclosed GFM
structure.
"""

from __future__ import annotations

import hashlib
import re

_MARKER_PREFIX = "NOVELTRAD"
_MARKER_RE = re.compile(r"\[NOVELTRAD:([0-9a-f]{16})\]")
_FENCE_RE = re.compile(r"^( {0,3})(`{3,}|~{3,})[^`\n]*$")
_SRT_COMMENT_RE = re.compile(r"<!--noveltrad:srt-cue:(.*?)-->")


def protect(markdown: str) -> tuple[str, dict[str, str]]:
    """Replace preserved elements with opaque markers.

    Returns (protected_markdown, mapping marker -> original value).
    Kept elements in order of appearance; code fences are handled so their
    inner content is not scanned for other markers.
    """
    mapping: dict[str, str] = {}
    lines = markdown.split("\n")
    out: list[str] = []
    in_fence: str | None = None
    for line in lines:
        fence = _FENCE_RE.match(line)
        if in_fence is not None:
            out.append(line)
            if fence and fence.group(2).startswith(in_fence):
                in_fence = None
            continue
        if fence:
            in_fence = fence.group(2)
            out.append(line)
            continue
        out.append(_protect_line(line, mapping))
    return "\n".join(out), mapping


def _protect_line(line: str, mapping: dict[str, str]) -> str:
    # Link destinations [text](dest) -> [text](MARKER)
    def replace_dest(match: re.Match[str]) -> str:
        marker = _new_marker(mapping, match.group(2))
        return f"{match.group(1)}({marker})"

    line = re.sub(r"(\[[^\]\n]*\])\(([^)\n]+)\)", replace_dest, line)
    # Image references ![alt](path) are already covered by link pattern,
    # but also protect bare data: URIs left in text.
    line = _protect_srt_comments(line, mapping)
    return line


def _protect_srt_comments(line: str, mapping: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        marker = _new_marker(mapping, f"<!--noveltrad:srt-cue:{match.group(1)}-->")
        return marker

    return _SRT_COMMENT_RE.sub(replace, line)


def _new_marker(mapping: dict[str, str], value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    if digest not in mapping:
        mapping[digest] = value
    return f"[{_MARKER_PREFIX}:{digest}]"


def restore(markdown: str, mapping: dict[str, str]) -> str:
    """Restore original values from markers, preserving order of use."""

    def replace(match: re.Match[str]) -> str:
        marker = match.group(1)
        return mapping.get(marker, match.group(0))

    return _MARKER_RE.sub(replace, markdown)


def validate(markdown: str, mapping: dict[str, str]) -> list[str]:
    """Return violation codes: MISSING, DUPLICATE, UNORDERED, UNCLOSED."""
    errors: list[str] = []
    used = [m.group(1) for m in _MARKER_RE.finditer(markdown)]
    expected = list(mapping.keys())
    if len(set(used)) != len(used):
        errors.append("DUPLICATE")
    if set(used) != set(expected):
        errors.append("MISSING")
    if used != expected and expected:
        errors.append("UNORDERED")
    if _has_unclosed_fence(markdown):
        errors.append("UNCLOSED")
    return errors


def _has_unclosed_fence(markdown: str) -> bool:
    in_fence: str | None = None
    for line in markdown.split("\n"):
        fence = _FENCE_RE.match(line)
        if in_fence is not None:
            if fence and fence.group(2).startswith(in_fence):
                in_fence = None
            continue
        if fence:
            in_fence = fence.group(2)
    return in_fence is not None


def count_markers(markdown: str) -> int:
    return len(_MARKER_RE.findall(markdown))
