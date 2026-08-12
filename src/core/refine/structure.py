"""Deterministic structure checks for plain-text and Markdown refinement."""

import re
from typing import Dict, List, Tuple


def _signature(text: str) -> Dict[str, List[str] | int]:
    return {
        "fences": len(re.findall(r"^\s*```", text or "", re.MULTILINE)),
        "links": re.findall(r"\[[^\]]*\]\(([^)]+)\)", text or ""),
        "headings": re.findall(r"^\s{0,3}#{1,6}\s", text or "", re.MULTILINE),
        "lists": re.findall(r"^\s*(?:[-*+]\s|\d+[.)]\s)", text or "", re.MULTILINE),
        "paragraph_breaks": len(re.findall(r"\n\s*\n", text or "")),
        "dialogue_markers": re.findall(
            r"^\s*(?:[-—]\s|[«\"“])", text or "", re.MULTILINE
        ),
        "placeholders": sorted(re.findall(
            r"(?:\[\[(?:id)?\d+\]\]|\[(?:id)?\d+\]|__TEMP_[A-Z_]+\d+__)",
            text or "",
        )),
    }


def is_plain_text_structure_safe(previous: str, candidate: str) -> bool:
    """Return False when refinement changes protected Markdown structure."""
    before = _signature(previous)
    after = _signature(candidate)
    return (
        before["fences"] == after["fences"]
        and before["links"] == after["links"]
        and before["headings"] == after["headings"]
        and before["lists"] == after["lists"]
        and before["paragraph_breaks"] == after["paragraph_breaks"]
        and before["dialogue_markers"] == after["dialogue_markers"]
        and before["placeholders"] == after["placeholders"]
    )
