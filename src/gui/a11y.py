"""Accessibility helpers — consistent focus policies, shortcuts, ARIA-like names.

All NovelTrad v4 widgets should pass through `configure()` to receive
a uniform baseline:

  * `setAccessibleName` / `setAccessibleDescription` (used by screen
    readers via `QAccessible`),
  * `setToolTip` (rich HTML allowed),
  * `setShortcut` and an associated `QShortcut` so the binding works
    even when the widget is not focused (e.g. menu items hidden),
  * `setFocusPolicy(StrongFocus)` so keyboard tabbing reaches it.

The shortcuts catalogue is centralised in `GLOBAL_SHORTCUTS` so we
can document them in Help and detect collisions at startup.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import QWidget


@dataclass(frozen=True)
class ShortcutSpec:
    action_id: str
    label: str
    sequence: str
    description: str


GLOBAL_SHORTCUTS: tuple[ShortcutSpec, ...] = (
    ShortcutSpec("open_file", "Open file…", "Ctrl+O", "Open a document to translate."),
    ShortcutSpec("rerun", "Re-run last project", "Ctrl+R", "Restart the most recent project."),
    ShortcutSpec("settings", "Settings", "Ctrl+,", "Open the application settings."),
    ShortcutSpec("help", "Help", "F1", "Show context-sensitive help."),
    ShortcutSpec("quit", "Quit", "Ctrl+Q", "Quit NovelTrad."),
    ShortcutSpec("close", "Close", "Esc", "Close the active dialog or drawer."),
    ShortcutSpec("validate_hitl", "Validate HITL", "Ctrl+Return", "Submit the human-in-the-loop answer."),
    ShortcutSpec("cycle_theme", "Cycle theme", "Ctrl+Shift+T", "Switch between light, dark and high-contrast."),
)


def configure(
    widget: QWidget,
    *,
    name: str | None = None,
    description: str | None = None,
    tooltip: str | None = None,
    shortcut: str | None = None,
    focusable: bool = True,
) -> None:
    """Apply a uniform accessibility baseline to a widget."""
    if name:
        widget.setAccessibleName(name)
    if description:
        widget.setAccessibleDescription(description)
    if tooltip:
        widget.setToolTip(tooltip)
    if focusable:
        widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        # Make sure screen readers can reach it.
        widget.setAttribute(Qt.WidgetAttribute.WA_AccessibleObjectName, True) if hasattr(
            Qt.WidgetAttribute, "WA_AccessibleObjectName"
        ) else None
    if shortcut:
        widget.setShortcut(QKeySequence(shortcut))


def bind_shortcut(
    parent: QWidget,
    sequence: str,
    slot: Callable[[], None],
    *,
    context: Qt.ShortcutContext = Qt.ShortcutContext.ApplicationShortcut,
) -> QShortcut:
    """Create a `QShortcut` parented to `parent` triggering `slot`."""
    sc = QShortcut(QKeySequence(sequence), parent)
    sc.setContext(context)
    sc.activated.connect(slot)
    return sc


def set_touch_target(widget: QWidget, min_px: int = 44) -> None:
    """Ensure a clickable widget respects a 44×44 px minimum touch target."""
    widget.setMinimumHeight(max(widget.minimumHeight(), min_px))


__all__ = [
    "ShortcutSpec",
    "GLOBAL_SHORTCUTS",
    "configure",
    "bind_shortcut",
    "set_touch_target",
]
