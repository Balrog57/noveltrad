"""Accessibility utilities (a11y) for PySide6 widgets."""

from typing import Any


def configure(
    widget: Any,
    accessible_name: str = "",
    tooltip: str = "",
    shortcut: str = "",
    focus_policy: Any = None,
) -> None:
    """Configure accessibility and UX properties for a widget."""
    if accessible_name:
        widget.setAccessibleName(accessible_name)
    if tooltip:
        widget.setToolTip(tooltip)
    if shortcut:
        widget.setShortcut(shortcut)
    if focus_policy is not None:
        widget.setFocusPolicy(focus_policy)
