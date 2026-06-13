"""Files tab — list of recent projects / output files.

In v4 minimal mode the "projects" we list are the chunks of the
current project. We show a small summary table and a button to
reopen a chunk detail.
"""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
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

    # Statuses that the user may want to replay selectively.
    _REPLAYABLE_STATUSES: tuple[str, ...] = ("error", "hash_mismatch", "waiting_for_human")

    def __init__(self, client: BackendClient, parent: QWidget | None = None):
        super().__init__(parent)
        self._client = client
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        layout.addWidget(QLabel(self.tr("Chunks of the current project")))

        # Filter bar above the table.
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel(self.tr("Filter by status:")))
        self._status_filter = QComboBox()
        self._status_filter.addItem(self.tr("All"), "")
        for st in self._REPLAYABLE_STATUSES:
            self._status_filter.addItem(st, st)
        self._status_filter.currentIndexChanged.connect(self.refresh)
        filter_row.addWidget(self._status_filter)
        filter_row.addStretch(1)
        layout.addLayout(filter_row)

        self._table = QTableWidget(0, 4)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)
        self._table.setHorizontalHeaderLabels(
            [self.tr("Chunk"), self.tr("Status"), self.tr("Chapter"), self.tr("Open")]
        )
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setStretchLastSection(False)
        self._table.cellDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self._table)

        row = QHBoxLayout()
        self._refresh_btn = QPushButton(self.tr("Refresh"))
        self._refresh_btn.clicked.connect(self.refresh)
        row.addWidget(self._refresh_btn)
        self._replay_selected_btn = QPushButton(self.tr("Replay selected"))
        self._replay_selected_btn.clicked.connect(self._on_replay_selected)
        self._replay_selected_btn.setToolTip(
            self.tr("Re-inject selected chunks into the pipeline")
        )
        row.addWidget(self._replay_selected_btn)
        self._replay_filtered_btn = QPushButton(self.tr("Replay filtered"))
        self._replay_filtered_btn.clicked.connect(self._on_replay_filtered)
        self._replay_filtered_btn.setToolTip(
            self.tr("Re-inject all chunks matching the current status filter")
        )
        row.addWidget(self._replay_filtered_btn)
        self._assemble_btn = QPushButton(self.tr("Assemble output…"))
        self._assemble_btn.clicked.connect(self._on_assemble)
        row.addWidget(self._assemble_btn)
        row.addStretch(1)
        self._status = QLabel("")
        row.addWidget(self._status)
        layout.addLayout(row)

    def refresh(self) -> None:
        self._table.setRowCount(0)
        self._status.setText("")
        filter_status = self._status_filter.currentData() or None
        try:
            params = {"limit": 200}
            if filter_status:
                params["status"] = filter_status
            data = self._client.get("/chunks", params=params, timeout=5.0) or {}
        except BackendError as exc:
            self._status.setText(
                self.tr("Backend unavailable: {err}").format(err=exc)
            )
            return
        chunks = data.get("chunks") or []
        for c in chunks:
            r = self._table.rowCount()
            self._table.insertRow(r)
            cid = c.get("id", "")
            self._table.setItem(r, 0, QTableWidgetItem(cid[:12]))
            self._table.item(r, 0).setData(Qt.ItemDataRole.UserRole, cid)
            status = c.get("status", "")
            status_item = QTableWidgetItem(status)
            if status in self._REPLAYABLE_STATUSES:
                status_item.setForeground(Qt.GlobalColor.red)
            self._table.setItem(r, 1, status_item)
            self._table.setItem(r, 2, QTableWidgetItem(c.get("chapter_title") or c.get("chapter_id") or ""))
            open_item = QTableWidgetItem(self.tr("View"))
            open_item.setData(Qt.ItemDataRole.UserRole, cid)
            open_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(r, 3, open_item)
        self._status.setText(self.tr("{n} chunks").format(n=len(chunks)))

    def _selected_chunk_ids(self) -> list[str]:
        ids: list[str] = []
        for index in self._table.selectionModel().selectedRows():
            row = index.row()
            item = self._table.item(row, 0)
            cid = item.data(Qt.ItemDataRole.UserRole) if item else None
            if cid:
                ids.append(str(cid))
        return ids

    def _on_double_click(self, row: int, col: int) -> None:
        if col != 3:
            return
        item = self._table.item(row, 3)
        cid = item.data(Qt.ItemDataRole.UserRole) if item else None
        if cid:
            self.chunkActivated.emit(str(cid))

    def _replay(self, chunk_ids: list[str]) -> None:
        if not chunk_ids:
            self._status.setText(self.tr("No chunks selected for replay."))
            return
        try:
            res = self._client.post(
                "/pipeline/replay-chunks",
                body={"chunk_ids": chunk_ids},
                timeout=10.0,
            )
            replayed = res.get("replayed", 0)
            self._status.setText(
                self.tr("Replayed {n} chunk(s)").format(n=replayed)
            )
            self.refresh()
        except BackendError as exc:
            self._status.setText(
                self.tr("Replay failed: {err}").format(err=exc)
            )

    def _on_replay_selected(self) -> None:
        self._replay(self._selected_chunk_ids())

    def _on_replay_filtered(self) -> None:
        try:
            params: dict[str, Any] = {"limit": 200}
            filter_status = self._status_filter.currentData() or None
            if filter_status:
                params["status"] = filter_status
            data = self._client.get("/chunks", params=params, timeout=5.0) or {}
            chunks = data.get("chunks") or []
        except BackendError as exc:
            self._status.setText(self.tr("Backend unavailable: {err}").format(err=exc))
            return
        self._replay([c["id"] for c in chunks])

    def _on_assemble(self) -> None:
        from PyQt6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Save assembled output"),
            "output.txt",
            self.tr(
                "Text (*.txt);;EPUB (*.epub);;DOCX (*.docx);;SRT (*.srt)"
            ),
        )
        if not path:
            return
        fmt = path.rsplit(".", 1)[-1].lower() or "txt"
        try:
            res = self._client.post(
                "/assemble", body={"output_path": path, "format": fmt}, timeout=10.0
            )
        except BackendError as exc:
            self._status.setText(
                self.tr("Assemble failed: {err}").format(err=exc)
            )
            return
        self._status.setText(
            self.tr("Dispatched ({n} chunks → {path})").format(
                n=res.get("chunk_count", 0), path=res.get("output_path")
            )
        )


__all__ = ["FilesTab"]
