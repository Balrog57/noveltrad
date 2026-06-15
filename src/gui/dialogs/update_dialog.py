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

from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
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

from src.gui.a11y import configure
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

        self.setWindowTitle(self.tr("Update available"))
        self.resize(560, 440)

        layout = QVBoxLayout(self)

        header = QLabel(
            self.tr("<h3>Version <b>{ver}</b> is available</h3>").format(
                ver=info.version
            )
            + self.tr("<p>You are running <b>{cur}</b>.</p>").format(
                cur=updater.current_version
            )
        )
        header.setTextFormat(Qt.TextFormat.RichText)
        header.setWordWrap(True)
        layout.addWidget(header)

        self._notes = QTextEdit()
        self._notes.setReadOnly(True)
        self._notes.setPlainText(info.body or self.tr("(no release notes)"))
        layout.addWidget(self._notes, 1)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFormat(self.tr("%p% — preparing…"))
        layout.addWidget(self._progress)

        self._status = QLabel("")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        # Buttons (custom, to control labels and behaviour).
        button_row = QHBoxLayout()
        self._github_btn = QPushButton(self.tr("View on GitHub"))
        self._github_btn.clicked.connect(self._open_github)
        configure(self._github_btn, name=self.tr("View release on GitHub"))
        button_row.addWidget(self._github_btn)
        button_row.addStretch(1)
        self._later_btn = QPushButton(self.tr("Later"))
        self._later_btn.clicked.connect(self.reject)
        configure(self._later_btn, name=self.tr("Update later"), shortcut="Esc")
        button_row.addWidget(self._later_btn)
        self._update_btn = QPushButton(self.tr("Update now"))
        self._update_btn.setDefault(True)
        self._update_btn.clicked.connect(self._start_download)
        configure(self._update_btn, name=self.tr("Update now"), shortcut="Ctrl+Return")
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
        self._progress.setFormat(self.tr("Downloading… %p%"))
        self._status.setText(self.tr("Downloading the installer…"))

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

    @pyqtSlot(int)
    def _set_progress(self, pct: int) -> None:
        self._progress.setValue(pct)

    @pyqtSlot()
    def _on_download_finished(self) -> None:
        if self._error or not self._downloaded_path:
            self._update_btn.setEnabled(True)
            self._github_btn.setEnabled(True)
            self._progress.setFormat(self.tr("Failed"))
            self._status.setText(
                self.tr("Download failed: {err}.\n").format(err=self._error or "unknown error")
                + self.tr("You can install the update manually from GitHub.")
            )
            self.updateFinished.emit(False, self._error or "download failed")
            return
        self._progress.setValue(100)
        self._progress.setFormat(self.tr("Downloaded — launching installer"))
        self._status.setText(self.tr("Installer downloaded. Launching it…"))
        self.updateStarted.emit(self._downloaded_path)
        try:
            self._updater.install(self._downloaded_path)
        except Exception as exc:  # noqa: BLE001
            logger.exception("updater: install launch failed: %s", exc)
            self._status.setText(
                self.tr("Could not launch installer: {err}.\n").format(err=exc)
                + self.tr("File saved to: {path}").format(path=self._downloaded_path)
            )
        self.updateFinished.emit(True, "ok")
        self.accept()


__all__ = ["UpdateDialog"]
