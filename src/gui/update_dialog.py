"""Update notification + download dialog (Qt).

Shown when a newer GitHub release is found. Lets the user read the release
notes and either download+apply the update or defer. The download + extraction
+ launcher hand-off runs in a QThread so the UI stays responsive.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QProgressBar,
    QTextEdit,
    QVBoxLayout,
)

from src.utils.updater import (
    LatestRelease,
    UpdateError,
    download_asset,
    extract_zip,
    perform_replace_and_relaunch,
)


class _ApplyWorker(QThread):
    """Downloads the new bundle, extracts it, and hands off to the updater.bat."""

    progress = Signal(int, int)  # (done_bytes, total_bytes)
    finished_ok = Signal(str)  # bat path or message
    failed = Signal(str)

    def __init__(self, release: LatestRelease) -> None:
        super().__init__()
        self.release = release

    def run(self) -> None:  # noqa: C901
        staging = Path(tempfile.mkdtemp(prefix="noveltrad_update_"))
        try:
            zip_path = staging / self.release.asset_name
            download_asset(
                self.release.asset_url,
                zip_path,
                progress_cb=lambda d, t: self.progress.emit(d, t),
            )
            new_dir = extract_zip(zip_path, staging / "extracted")
            bat = perform_replace_and_relaunch(new_dir)
            self.finished_ok.emit(str(bat))
        except UpdateError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(f"{type(exc).__name__}: {exc}")


class UpdateDialog(QDialog):
    """Modal offering to download and apply a newer release."""

    def __init__(self, release: LatestRelease, parent=None) -> None:
        super().__init__(parent)
        self.release = release
        self._worker: _ApplyWorker | None = None
        self.setWindowTitle("Mise à jour disponible")
        self.setMinimumWidth(460)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        from src.utils.updater import get_current_version

        title = QLabel(
            f"<b>AgentTranslate v{self.release.version}</b> est disponible "
            f"(vous avez la v{get_current_version()})."
        )
        title.setWordWrap(True)
        layout.addWidget(title)

        notes_label = QLabel("Notes de version :")
        layout.addWidget(notes_label)
        notes = QTextEdit()
        notes.setReadOnly(True)
        notes.setPlainText(self.release.notes or "(aucune note)")
        notes.setMaximumHeight(180)
        layout.addWidget(notes)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.status = QLabel("")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        self.buttons = QDialogButtonBox()
        self.download_btn = self.buttons.addButton(
            "Télécharger et installer", QDialogButtonBox.ButtonRole.AcceptRole
        )
        self.later_btn = self.buttons.addButton(
            "Plus tard", QDialogButtonBox.ButtonRole.RejectRole
        )
        self.download_btn.clicked.connect(self._on_download)
        layout.addWidget(self.buttons)

    def _on_download(self) -> None:
        self.download_btn.setEnabled(False)
        self.later_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.status.setText("Téléchargement en cours…")
        self._worker = _ApplyWorker(self.release)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_ok.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_progress(self, done: int, total: int) -> None:
        if total > 0:
            self.progress.setMaximum(total)
            self.progress.setValue(done)
            mb = done / (1024 * 1024)
            tot_mb = total / (1024 * 1024)
            self.status.setText(f"Téléchargement… {mb:.0f} / {tot_mb:.0f} Mo")
        else:
            self.progress.setRange(0, 0)  # indeterminate

    def _on_finished(self, _bat_path: str) -> None:
        self.status.setText("✅ Mise à jour préparée — l'application va redémarrer.")
        QMessageBox.information(
            self, "Redémarrage",
            "L'application va se fermer pour appliquer la mise à jour, puis redémarrer.",
        )
        self.accept()
        # The app.py controller watches dialog exit; on accept it quits the app.

    def _on_failed(self, msg: str) -> None:
        self.progress.setVisible(False)
        self.status.setText(f"❌ {msg}")
        self.download_btn.setEnabled(True)
        self.later_btn.setEnabled(True)


def _current() -> str:
    from src.utils.updater import get_current_version

    return get_current_version()
