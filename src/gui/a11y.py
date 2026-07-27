from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

def configure(
    widget: Any,
    accessible_name: str,
    tooltip: str = "",
    shortcut: str = "",
    focus_policy: int | None = None,
) -> None:
    """Applies accessibility and UX properties to a widget."""
    if accessible_name:
        widget.setAccessibleName(accessible_name)
    if tooltip:
        widget.setToolTip(tooltip)
    if shortcut:
        widget.setShortcut(shortcut)
    if focus_policy is not None:
        widget.setFocusPolicy(focus_policy)
