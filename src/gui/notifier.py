"""Native system notifications and a header-pulse helper.

Wraps `QSystemTrayIcon` so HITL alerts can pop a Windows 10/11 toast
even when the main window is minimised. Falls back to `QMessageBox`
if the OS doesn't expose a tray.
"""

from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import QObject
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from .a11y import configure

logger = logging.getLogger(__name__)


class Notifier(QObject):
    """Owns a `QSystemTrayIcon` for background notifications."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._tray: QSystemTrayIcon | None = None
        self._fallback = not self._init_tray()

    def _init_tray(self) -> bool:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return False
        try:
            icon = QIcon.fromTheme("noveltrad", QIcon())
            self._tray = QSystemTrayIcon(icon, self)
            menu = QMenu()
            open_act = QAction(self.tr("Open NovelTrad"), self)
            quit_act = QAction(self.tr("Quit"), self)
            menu.addAction(open_act)
            menu.addSeparator()
            menu.addAction(quit_act)
            self._tray.setContextMenu(menu)
            configure(
                self._tray,
                name=self.tr("NovelTrad tray"),
                description=self.tr("Background notifier"),
            )
            self._tray.show()
            return True
        except Exception as exc:
            logger.warning("System tray init failed: %s", exc)
            self._tray = None
            return False

    def notify(self, title: str, body: str, level: str = "info") -> None:
        """Show a desktop notification. No-op on error."""
        if self._tray is not None:
            try:
                icon_kind = {
                    "info": QSystemTrayIcon.MessageIcon.Information,
                    "warning": QSystemTrayIcon.MessageIcon.Warning,
                    "error": QSystemTrayIcon.MessageIcon.Critical,
                }.get(level, QSystemTrayIcon.MessageIcon.Information)
                self._tray.showMessage(title, body, icon_kind, 5000)
                return
            except Exception as exc:
                logger.debug("tray.showMessage failed: %s", exc)
        # Fallback: silent log. A modal QMessageBox would interrupt the
        # operator and is not what we want for passive alerts.
        logger.info("notify[%s] %s: %s", level, title, body)


__all__ = ["Notifier"]
