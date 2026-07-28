"""Accessibility utilities for PySide6 widgets."""

from typing import Any

from PySide6.QtCore import Qt


def configure(
    widget: Any,
    accessible_name: str | None = None,
    tooltip: str | None = None,
    shortcut: str | None = None,
    focusable: bool | None = None,
) -> None:
    """Apply standard accessibility and UX properties to a widget."""
    if accessible_name is not None:
        widget.setAccessibleName(accessible_name)
    if tooltip is not None:
        widget.setToolTip(tooltip)
    if shortcut is not None and hasattr(widget, "setShortcut"):
        widget.setShortcut(shortcut)
    if focusable is not None:
        widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus if focusable else Qt.FocusPolicy.NoFocus)
