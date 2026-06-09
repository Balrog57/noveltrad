"""Files tab — list of recent projects / output files.

In v4 minimal mode the "projects" we list are the chunks of the
current project. We show a small summary table and a button to
reopen a chunk detail.
"""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.gui.backend_client import BackendClient, BackendError


class FilesTab(QWidget):
    chunkActivated = pyqtSignal(str)  # chunk_id

    def __init__(self, client: BackendClient, parent: QWidget | None = None):
        super().__init__(parent)
        self._client = client
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        layout.addWidget(QLabel("Chunks of the current project"))

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Chunk", "Status", "Chapter", "Open"])
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._table.cellDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self._table)

        row = QHBoxLayout()
        self._refresh_btn = QPushButton("Refresh")
        self._refresh_btn.clicked.connect(self.refresh)
        row.addWidget(self._refresh_btn)
        self._assemble_btn = QPushButton("Assemble output…")
        self._assemble_btn.clicked.connect(self._on_assemble)
        row.addWidget(self._assemble_btn)
        row.addStretch(1)
        self._status = QLabel("")
        row.addWidget(self._status)
        layout.addLayout(row)

        self.refresh()

    def refresh(self) -> None:
        self._table.setRowCount(0)
        try:
            data = self._client.get("/chunks?limit=200", timeout=5.0) or {}
        except BackendError as exc:
            self._status.setText(f"Backend unavailable: {exc}")
            return
        chunks = data.get("chunks") or []
        for c in chunks:
            r = self._table.rowCount()
            self._table.insertRow(r)
            cid = c.get("id", "")
            self._table.setItem(r, 0, QTableWidgetItem(cid[:12]))
            self._table.setItem(r, 1, QTableWidgetItem(c.get("status", "")))
            self._table.setItem(r, 2, QTableWidgetItem(c.get("chapter_title") or c.get("chapter_id") or ""))
            open_item = QTableWidgetItem("View")
            open_item.setData(Qt.ItemDataRole.UserRole, cid)
            open_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(r, 3, open_item)
        self._status.setText(f"{len(chunks)} chunks")

    def _on_double_click(self, row: int, col: int) -> None:
        if col != 3:
            return
        item = self._table.item(row, 3)
        cid = item.data(Qt.ItemDataRole.UserRole) if item else None
        if cid:
            self.chunkActivated.emit(str(cid))

    def _on_assemble(self) -> None:
        from PyQt6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getSaveFileName(
            self, "Save assembled output", "output.txt", "Text (*.txt);;EPUB (*.epub);;DOCX (*.docx);;SRT (*.srt)"
        )
        if not path:
            return
        fmt = path.rsplit(".", 1)[-1].lower() or "txt"
        try:
            res = self._client.post(
                "/assemble", body={"output_path": path, "format": fmt}, timeout=10.0
            )
        except BackendError as exc:
            self._status.setText(f"Assemble failed: {exc}")
            return
        self._status.setText(
            f"Dispatched ({res.get('chunk_count', 0)} chunks → {res.get('output_path')})"
        )


__all__ = ["FilesTab"]
