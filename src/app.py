"""Application entry point (CDC §6 — src/app.py).

Wires together: QApplication, MainWindow, System Tray (F3), Global Hotkey
Ctrl+Alt+T (F1.c), and the selection overlay (F3.c).
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from src.gui.hotkey import GlobalHotkey
from src.gui.main_window import MainWindow
from src.gui.overlay import SelectionTranslator
from src.gui.tray import TrayIcon
from src.utils.config import Config


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("AgentTranslate")
    app.setOrganizationName("NovelTrad")
    # Application du style global Windows/Sombre optionnel.
    app.setStyle("Fusion")

    config = Config()

    window = MainWindow(config)
    window.show()

    # Selection translator (F1.c overlay) — attached to the window so the tray
    # menu can also trigger it.
    translator = SelectionTranslator(config)
    window._overlay = translator  # type: ignore[attr-defined]

    # System tray (F3).
    tray = TrayIcon(window)
    window._tray = tray  # type: ignore[attr-defined]
    tray.show()

    # Global hotkey Ctrl+Alt+T (F1.c).
    hotkey = GlobalHotkey(translator.translate_selection)
    hotkey.start()

    exit_code = app.exec()

    hotkey.stop()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
