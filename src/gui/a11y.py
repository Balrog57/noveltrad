"""Accessibility utilities for PySide6 widgets."""

from typing import Any

from PySide6.QtCore import Qt


def configure(
    widget: Any,
    *,
    accessible_name: str | None = None,
    tooltip: str | None = None,
    shortcut: str | None = None,
    focus_policy: Qt.FocusPolicy | None = None,
) -> None:
    """
    Apply generic accessibility configurations to a PySide6 widget.

    Args:
        widget: The Qt widget to configure (Any to avoid subclass strict typing issues).
        accessible_name: Sets the AccessibleName for screen readers.
        tooltip: Sets the ToolTip for mouse users.
        shortcut: Sets the keyboard shortcut.
        focus_policy: Sets the Qt focus policy.
    """
    if accessible_name is not None:
        widget.setAccessibleName(accessible_name)

    if tooltip is not None:
        widget.setToolTip(tooltip)

    if shortcut is not None and hasattr(widget, "setShortcut"):
        widget.setShortcut(shortcut)

    if focus_policy is not None:
        widget.setFocusPolicy(focus_policy)
