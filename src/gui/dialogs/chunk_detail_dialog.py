"""Chunk detail dialog — read-only view of a chunk's translation history.

Shows the chain of intermediate translations (raw, glossary, qa,
grammar, polished) plus the issues flagged by each stage.
"""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
)

from src.gui.backend_client import BackendClient, BackendError


class ChunkDetailDialog(QDialog):
    def __init__(self, chunk_id: str, client: BackendClient, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Chunk {chunk_id[:12]}")
        self.resize(720, 560)
        self._client = client
        self._chunk_id = chunk_id
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        header.addWidget(QLabel(f"<b>ID:</b> {chunk_id}"))
        header.addStretch(1)
        reprocess_btn = QPushButton("Reprocess")
        reprocess_btn.clicked.connect(self._reprocess)
        header.addWidget(reprocess_btn)
        layout.addLayout(header)

        self._tabs = QTabWidget()
        for label in (
            "Source",
            "Raw (NLLB)",
            "Glossary",
            "QA",
            "Grammar",
            "Polished",
            "Status",
        ):
            self._tabs.addTab(QTextEdit(), label)
        layout.addWidget(self._tabs)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        self.refresh()

    def _set_text(self, idx: int, text: str) -> None:
        w = self._tabs.widget(idx)
        if isinstance(w, QTextEdit):
            w.setPlainText(text or "(empty)")

    def refresh(self) -> None:
        try:
            c = self._client.get(f"/chunks/{self._chunk_id}", timeout=5.0)
        except BackendError as exc:
            self._set_text(0, f"Backend error: {exc}")
            return
        if not c:
            return
        self._set_text(0, c.get("source_text", ""))
        self._set_text(1, c.get("raw_translation", ""))
        self._set_text(2, c.get("glossary_applied", ""))
        self._set_text(3, c.get("qa_checked", ""))
        self._set_text(4, c.get("grammar_checked", ""))
        self._set_text(5, c.get("polished_translation", ""))
        meta = (
            f"Status: {c.get('status', '')}\n"
            f"Chapter: {c.get('chapter_title') or c.get('chapter_id', '')}\n"
            f"Chunk #: {c.get('chunk_index', '')}\n"
            f"Source hash: {c.get('source_hash', '')}\n"
            f"Error: {c.get('error_message') or 'none'}"
        )
        self._set_text(6, meta)

    def _reprocess(self) -> None:
        try:
            self._client.post(
                f"/chunks/{self._chunk_id}/reprocess", timeout=5.0
            )
        except BackendError as exc:
            self._set_text(6, f"Reprocess failed: {exc}")
            return
        self._set_text(6, "Reprocess queued.")


__all__ = ["ChunkDetailDialog"]
