"""GFM validation for verification (SDD 11.12)."""

from __future__ import annotations

from noveltrad.modules.documents.adapters.markdown import GfmValidator


def validate_gfm(markdown: str) -> list[str]:
    """Return [] when structurally valid, else a violation code."""
    if not markdown or not markdown.strip():
        return ["EMPTY"]
    validator = GfmValidator()
    if not validator.is_valid(markdown):
        return ["GFM_INVALID"]
    return []
