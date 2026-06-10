"""Update dialog — confirms + downloads + launches a new release.

Lives in :mod:`src.gui.dialogs` next to the other modal helpers. The
dialog is intentionally simple: a header with the version diff, the
release notes body, a progress bar that shows download progress, and
three buttons (``Update now`` / ``Later`` / ``View on GitHub``).

The dialog never raises on network/parse errors; it falls back to
displaying the GitHub URL so the user can finish the update manually.
"""

from __future__ import annotations

import logging
import threading
import webbrowser
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from src.gui.updater import Updater, UpdateInfo, download_default_destination


logger = logging.getLogger(__name__)


class UpdateDialog(QDialog):
    """Modal dialog that walks the user through an auto-update."""

    updateStarted = pyqtSignal(Path)
    updateFinished = pyqtSignal(bool, str)  # ok, message

    def __init__(
        self,
        updater: Updater,
        info: UpdateInfo,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._updater = updater
        self._info = info
        self._downloaded_path: Optional[Path] = None
        self._error: Optional[str] = None

        self.setWindowTitle("Update available")
        self.resize(560, 440)

        layout = QVBoxLayout(self)

        header = QLabel(
            f"<h3>Version <b>{info.version}</b> is available</h3>"
            f"<p>You are running <b>{updater.current_version}</b>.</p>"
        )
        header.setTextFormat(Qt.TextFormat.RichText)
        header.setWordWrap(True)
        layout.addWidget(header)

        self._notes = QTextEdit()
        self._notes.setReadOnly(True)
        self._notes.setPlainText(info.body or "(no release notes)")
        layout.addWidget(self._notes, 1)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFormat("%p% — preparing…")
        layout.addWidget(self._progress)

        self._status = QLabel("")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        # Buttons (custom, to control labels and behaviour).
        button_row = QHBoxLayout()
        self._github_btn = QPushButton("View on GitHub")
        self._github_btn.clicked.connect(self._open_github)
        button_row.addWidget(self._github_btn)
        button_row.addStretch(1)
        self._later_btn = QPushButton("Later")
        self._later_btn.clicked.connect(self.reject)
        button_row.addWidget(self._later_btn)
        self._update_btn = QPushButton("Update now")
        self._update_btn.setDefault(True)
        self._update_btn.clicked.connect(self._start_download)
        button_row.addWidget(self._update_btn)
        layout.addLayout(button_row)

    # ------------------------------------------------------------------

    @property
    def info(self) -> UpdateInfo:
        return self._info

    def _open_github(self) -> None:
        url = self._info.download_url or f"https://github.com/Balrog57/noveltrad/releases/tag/{self._info.tag}"
        try:
            QDesktopServices.openUrl(QUrl(url))
        except Exception:
            try:
                webbrowser.open(url)
            except Exception:
                logger.exception("Failed to open %s", url)

    def _start_download(self) -> None:
        self._update_btn.setEnabled(False)
        self._github_btn.setEnabled(False)
        self._progress.setFormat("Downloading… %p%")
        self._status.setText("Downloading the installer…")

        def worker() -> None:
            try:
                dest = self._updater.download(
                    self._info,
                    dest=download_default_destination()
                    / f"NovelTrad-setup-{self._info.version}.exe",
                    progress_cb=self._on_progress,
                    timeout=120.0,
                )
                self._downloaded_path = dest
            except Exception as exc:  # noqa: BLE001
                logger.warning("updater: download failed: %s", exc)
                self._error = str(exc)
            finally:
                # Hop back to the GUI thread.
                from PyQt6.QtCore import QMetaObject, Qt as _Qt, Q_ARG

                QMetaObject.invokeMethod(
                    self,
                    "_on_download_finished",
                    _Qt.ConnectionType.QueuedConnection,
                )

        threading.Thread(target=worker, daemon=True).start()

    def _on_progress(self, downloaded: int, total: int) -> None:
        if total <= 0:
            pct = 0
        else:
            pct = int(downloaded * 100 / total)
        # Use a queued signal-like invoke from the worker thread.
        from PyQt6.QtCore import QMetaObject, Qt as _Qt, Q_ARG

        QMetaObject.invokeMethod(
            self,
            "_set_progress",
            _Qt.ConnectionType.QueuedConnection,
            Q_ARG(int, pct),
        )

    def _set_progress(self, pct: int) -> None:  # Qt slot
        self._progress.setValue(pct)

    def _on_download_finished(self) -> None:  # Qt slot
        if self._error or not self._downloaded_path:
            self._update_btn.setEnabled(True)
            self._github_btn.setEnabled(True)
            self._progress.setFormat("Failed")
            self._status.setText(
                f"Download failed: {self._error or 'unknown error'}.\n"
                "You can install the update manually from GitHub."
            )
            self.updateFinished.emit(False, self._error or "download failed")
            return
        self._progress.setValue(100)
        self._progress.setFormat("Downloaded — launching installer")
        self._status.setText("Installer downloaded. Launching it…")
        self.updateStarted.emit(self._downloaded_path)
        try:
            self._updater.install(self._downloaded_path)
        except Exception as exc:  # noqa: BLE001
            logger.exception("updater: install launch failed: %s", exc)
            self._status.setText(
                f"Could not launch installer: {exc}.\n"
                f"File saved to: {self._downloaded_path}"
            )
        self.updateFinished.emit(True, "ok")
        self.accept()


__all__ = ["UpdateDialog"]
