"""Application entry point (CDC §6 — src/app.py).

Wires together: QApplication, MainWindow, System Tray (F3), Global Hotkey
Ctrl+Alt+T (F1.c), the selection overlay (F3.c), and the auto-update check.
"""

from __future__ import annotations

import sys

from PySide6.QtCore import QObject, QThread, QTimer, Signal
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from src.gui.hotkey import GlobalHotkey
from src.gui.main_window import MainWindow
from src.gui.overlay import SelectionTranslator
from src.gui.tray import TrayIcon
from src.gui.update_dialog import UpdateDialog
from src.utils.config import Config
from src.utils.updater import (
    LatestRelease,
    UpdateError,
    fetch_latest_release,
    get_current_version,
    is_newer,
    is_packaged,
)


class _CheckWorker(QThread):
    """Fetches the latest release off the UI thread."""

    found = Signal(object)  # LatestRelease
    failed = Signal(str)
    no_update = Signal()

    def run(self) -> None:
        try:
            release = fetch_latest_release()
        except UpdateError as exc:
            self.failed.emit(str(exc))
            return
        if is_newer(release.version, get_current_version()):
            self.found.emit(release)
        else:
            self.no_update.emit()


class UpdateController(QObject):
    """Drives the update check + dialog lifecycle, bound to the tray + window."""

    def __init__(self, window, tray) -> None:
        super().__init__()
        self.window = window
        self.tray = tray
        self._worker: _CheckWorker | None = None

    def check(self, silent: bool = True) -> None:
        """silent=True (startup) suppresses the 'no update' / error noise."""
        # Skip in dev mode — replacing source code makes no sense.
        if not is_packaged():
            if not silent:
                QMessageBox.information(
                    self.window, "Mises à jour",
                    "Mode développement : l'auto-update n'est actif que sur la version packagée.",
                )
            return
        self._worker = _CheckWorker()
        self._worker.found.connect(self._on_found)
        if silent:
            self._worker.failed.connect(lambda _msg: None)
            self._worker.no_update.connect(lambda: None)
        else:
            self._worker.no_update.connect(
                lambda: QMessageBox.information(
                    self.window, "Mises à jour",
                    f"AgentTranslate est à jour (v{get_current_version()}).",
                )
            )
            self._worker.failed.connect(
                lambda msg: QMessageBox.warning(self.window, "Mise à jour", msg)
            )
        self._worker.start()

    def _on_found(self, release: LatestRelease) -> None:
        version = release.version
        self.tray.showMessage(
            "AgentTranslate",
            f"v{version} est disponible. Cliquez pour installer.",
        )
        dlg = UpdateDialog(release, self.window)
        dlg.exec()
        # If the user accepted (download done), the updater.bat is waiting for
        # the app to exit — quit now.
        if dlg.result() == QDialog.DialogCode.Accepted:
            QApplication.quit()


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

    # Auto-update controller — referenced by the tray 'check for updates' action.
    updater = UpdateController(window, tray)
    window._updater = updater  # type: ignore[attr-defined]
    tray.check_updates = lambda: updater.check(silent=False)  # type: ignore[attr-defined]

    # Check for updates a few seconds after startup (non-blocking) if enabled.
    if config.get("check_updates_on_startup", True):
        QTimer.singleShot(3000, lambda: updater.check(silent=True))

    # Global hotkey Ctrl+Alt+T (F1.c).
    hotkey = GlobalHotkey(translator.translate_selection)
    hotkey.start()

    exit_code = app.exec()

    hotkey.stop()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())

