"""Accessibility utilities."""
from typing import Any


def configure(
    widget: Any,
    accessible_name: str | None = None,
    tooltip: str | None = None,
    shortcut: str | None = None,
    focus_policy: Any | None = None,
) -> None:
    """Configures accessibility properties for a PySide6 widget."""
    if accessible_name is not None:
        widget.setAccessibleName(accessible_name)
    if tooltip is not None:
        widget.setToolTip(tooltip)
    if shortcut is not None and hasattr(widget, "setShortcut"):
        widget.setShortcut(shortcut)
    if focus_policy is not None:
        widget.setFocusPolicy(focus_policy)
