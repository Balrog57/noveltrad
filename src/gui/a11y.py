from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QWidget

def configure(
    widget: QWidget,
    accessible_name: str = "",
    tooltip: str = "",
    shortcut: str = "",
    focus_policy: Qt.FocusPolicy | None = None,
) -> None:
    """Apply ARIA-like labels and UX properties to PySide6 widgets."""
    if accessible_name:
        widget.setAccessibleName(accessible_name)
    if tooltip:
        widget.setToolTip(tooltip)
    if shortcut and hasattr(widget, "setShortcut"):
        widget.setShortcut(shortcut)  # type: ignore
    if focus_policy is not None:
        widget.setFocusPolicy(focus_policy)
