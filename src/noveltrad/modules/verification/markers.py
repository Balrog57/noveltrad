"""Marker validation helpers (SDD 11.11, verification)."""

from __future__ import annotations

import re

_MARKER_RE = re.compile(r"\[NOVELTRAD:([0-9a-f]{16})\]")


def extract_markers(markdown: str) -> list[str]:
    return _MARKER_RE.findall(markdown)


def markers_preserved(content: str, source: str) -> list[str]:
    """Return violation codes; empty when every source marker appears
    exactly once and in the same order in the content (11.11)."""
    errors: list[str] = []
    expected = extract_markers(source)
    actual = extract_markers(content)
    if len(set(actual)) != len(actual):
        errors.append("DUPLICATE_MARKER")
    if set(actual) != set(expected):
        errors.append("MISSING_MARKER")
    if actual != expected and expected:
        errors.append("MARKER_ORDER")
    return errors
