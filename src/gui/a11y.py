from typing import Any


def configure(
    widget: Any,
    accessible_name: str | None = None,
    tooltip: str | None = None,
) -> None:
    if accessible_name is not None:
        widget.setAccessibleName(accessible_name)
    if tooltip is not None:
        widget.setToolTip(tooltip)
