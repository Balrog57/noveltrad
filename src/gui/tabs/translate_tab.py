"""Translate tab — drop zone, language selectors, Start button.

Mirrors the TBL UX. Drops a file → POST /projects → orchestrator
parses and the activity log shows progress. Start button enables once
a file is dropped.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)

LANGUAGES: list[tuple[str, str]] = [
    ("auto", "Auto-detect"),
    ("en", "English"),
    ("fr", "Français"),
    ("es", "Español"),
    ("de", "Deutsch"),
    ("it", "Italiano"),
    ("pt", "Português"),
    ("ru", "Русский"),
    ("zh", "中文"),
    ("ja", "日本語"),
    ("ko", "한국어"),
]


class _DropZone(QFrame):
    fileDropped = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            "QFrame { border: 2px dashed #555; border-radius: 12px; padding: 24px; }"
        )
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon = QLabel("☁")
        self._icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon.setStyleSheet("font-size: 36pt;")
        layout.addWidget(self._icon)
        self._hint = QLabel("Drop files to translate")
        self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint.setStyleSheet("font-size: 12pt;")
        layout.addWidget(self._hint)
        self._sub = QLabel("Support for TXT, EPUB, SRT, and DOCX")
        self._sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._sub.setStyleSheet("color: #888;")
        layout.addWidget(self._sub)
        self._browse = QPushButton("Browse Files")
        self._browse.clicked.connect(self._open_dialog)
        layout.addWidget(self._browse, alignment=Qt.AlignmentFlag.AlignCenter)
        self._path_label = QLabel("")
        self._path_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._path_label.setStyleSheet("color: #7be395;")
        self._path_label.setWordWrap(True)
        layout.addWidget(self._path_label)
        self._dropped: str | None = None

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        if not urls:
            return
        local = urls[0].toLocalFile()
        if local:
            self.set_path(local)
            self.fileDropped.emit(local)
            event.acceptProposedAction()

    def _open_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select a file to translate",
            "",
            "Documents (*.epub *.docx *.txt *.srt);;All files (*.*)",
        )
        if path:
            self.set_path(path)
            self.fileDropped.emit(path)

    def set_path(self, path: str) -> None:
        self._dropped = path
        p = Path(path)
        self._path_label.setText(p.name)
        self._hint.setText("File ready")
        self._icon.setText("📄")


class TranslateTab(QWidget):
    startRequested = pyqtSignal(dict)  # { source_path, source_lang, target_lang, project_dir }
    fileSelected = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None, default_target: str = "fr"):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        lang_row = QHBoxLayout()
        lang_row.addWidget(QLabel("SOURCE LANG"))
        self._src = QComboBox()
        for code, label in LANGUAGES:
            self._src.addItem(label, code)
        lang_row.addWidget(self._src, 1)
        lang_row.addSpacing(20)
        lang_row.addWidget(QLabel("TARGET LANG"))
        self._tgt = QComboBox()
        for code, label in LANGUAGES:
            if code == "auto":
                continue
            self._tgt.addItem(label, code)
        idx = self._tgt.findData(default_target)
        if idx >= 0:
            self._tgt.setCurrentIndex(idx)
        lang_row.addWidget(self._tgt, 1)
        layout.addLayout(lang_row)

        self._drop = _DropZone()
        self._drop.fileDropped.connect(self._on_file)
        layout.addWidget(self._drop, 1)

        self._start_btn = QPushButton("▶  Start Translation Batch")
        self._start_btn.setStyleSheet(
            "QPushButton { padding: 12px 24px; font-size: 12pt; font-weight: 600; }"
            "QPushButton:disabled { color: #666; }"
        )
        self._start_btn.setEnabled(False)
        self._start_btn.clicked.connect(self._on_start)
        layout.addWidget(self._start_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self._status = QLabel("")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setStyleSheet("color: #888;")
        layout.addWidget(self._status)

        self._selected_path: str | None = None
        self._project_dir: str = ""

    def set_project_dir(self, project_dir: str) -> None:
        self._project_dir = project_dir

    def set_status(self, text: str) -> None:
        self._status.setText(text)

    def _on_file(self, path: str) -> None:
        self._selected_path = path
        self._start_btn.setEnabled(True)
        self.fileSelected.emit(path)

    def _on_start(self) -> None:
        if not self._selected_path:
            return
        payload = {
            "source_path": self._selected_path,
            "source_lang": self._src.currentData() or "auto",
            "target_lang": self._tgt.currentData() or "fr",
            "project_dir": self._project_dir or str(Path(self._selected_path).parent),
        }
        self.startRequested.emit(payload)
        self.set_status(
            f"Queued: {Path(self._selected_path).name} "
            f"({payload['source_lang']} → {payload['target_lang']})"
        )


__all__ = ["TranslateTab"]
