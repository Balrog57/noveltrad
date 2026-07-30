"""Accessibility utilities."""

from __future__ import annotations

from typing import Any


def configure(
    widget: Any,
    accessible_name: str | None = None,
    tooltip: str | None = None,
) -> None:
    """Configure accessibility and UX properties for a widget."""
    if accessible_name is not None:
        widget.setAccessibleName(accessible_name)
    if tooltip is not None:
        widget.setToolTip(tooltip)
