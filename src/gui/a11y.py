"""Accessibility utilities for PySide6 widgets."""

from typing import Any


def configure(widget: Any, accessible_name: str = "", tooltip: str = "") -> None:
    """Configure accessibility and tooltip properties for a PySide6 widget.

    Args:
        widget: The PySide6 widget (e.g., QPushButton). We use Any to avoid
            strict type checking issues with QWidget subclasses.
        accessible_name: The screen-reader accessible name.
        tooltip: The hover tooltip.
    """
    if accessible_name:
        widget.setAccessibleName(accessible_name)
    if tooltip:
        widget.setToolTip(tooltip)
