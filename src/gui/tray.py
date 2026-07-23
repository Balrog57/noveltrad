"""System tray icon (CDC F3 + §5 'Exécution possible en tâche de fond').

Minimize-to-tray, restore window, quit. Keeps the app running in the background
so the global hotkey (Ctrl+Alt+T) stays active.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QAction, QIcon, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon, QWidget


def _make_icon() -> QIcon:
    """Load the bundled icon, or fall back to a generated square."""
    icon_path = Path(__file__).resolve().parents[2] / "assets" / "icon.ico"
    if icon_path.exists():
        return QIcon(str(icon_path))
    # Fallback: a simple coloured pixmap.
    pix = QPixmap(64, 64)
    pix.fill()  # white
    return QIcon(pix)


class TrayIcon(QSystemTrayIcon):
    def __init__(self, window: QWidget) -> None:
        super().__init__(_make_icon(), window)
        self.window = window
        self.setToolTip("AgentTranslate — Multi-Agent Translation")

        menu = QMenu()
        show_action = QAction("Afficher", menu)
        show_action.triggered.connect(self._show_window)
        menu.addAction(show_action)

        translate_action = QAction("Traduire la sélection (Ctrl+Alt+T)", menu)
        translate_action.triggered.connect(self._trigger_overlay)
        menu.addAction(translate_action)

        menu.addSeparator()
        quit_action = QAction("Quitter", menu)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)

        self.setContextMenu(menu)
        self.activated.connect(self._on_activated)

    def _on_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_window()

    def _show_window(self) -> None:
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()

    def _trigger_overlay(self) -> None:
        # Delegated to the app/hotkey controller if present.
        overlay = getattr(self.window, "_overlay", None)
        if overlay is not None:
            overlay.translate_selection()

    def _quit(self) -> None:
        self.window._force_quit = True  # type: ignore[attr-defined]
        self.hide()
        from PySide6.QtWidgets import QApplication

        QApplication.quit()
