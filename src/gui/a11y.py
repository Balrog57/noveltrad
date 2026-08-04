"""Accessibility utilities for the PySide6 UI."""

from typing import Any


def configure(
    widget: Any,
    accessible_name: str | None = None,
    tooltip: str | None = None,
    shortcut: str | None = None,
    focus_policy: Any = None,
) -> None:
    """Configure common accessibility properties on a PySide6 widget.

    Args:
        widget: The widget to configure (e.g. QWidget, QAbstractButton).
        accessible_name: Screen reader label.
        tooltip: Visual tooltip on hover.
        shortcut: Keyboard shortcut (for buttons/actions).
        focus_policy: Qt.FocusPolicy for keyboard navigation.
    """
    if accessible_name is not None:
        widget.setAccessibleName(accessible_name)
    if tooltip is not None:
        widget.setToolTip(tooltip)
    if shortcut is not None and hasattr(widget, "setShortcut"):
        widget.setShortcut(shortcut)
    if focus_policy is not None and hasattr(widget, "setFocusPolicy"):
        widget.setFocusPolicy(focus_policy)
