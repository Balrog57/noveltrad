"""Glossaries tab — editable table of source->target terms.

Backed by the `/lexicon` REST API. The table supports add/edit/
delete and import/export (JSON).
"""

from __future__ import annotations

import json
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.gui.backend_client import BackendClient, BackendError


class GlossariesTab(QWidget):
    def __init__(self, client: BackendClient, parent: QWidget | None = None):
        super().__init__(parent)
        self._client = client
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        header_row = QHBoxLayout()
        header_row.addWidget(QLabel(self.tr("Lexicon (source → target)")))
        header_row.addStretch(1)
        self._filter = QLineEdit()
        self._filter.setPlaceholderText(self.tr("Filter…"))
        self._filter.textChanged.connect(self._apply_filter)
        header_row.addWidget(self._filter)
        layout.addLayout(header_row)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            [
                self.tr("Source"),
                self.tr("Target"),
                self.tr("Category"),
                self.tr("Gender"),
                self.tr("Confidence"),
            ]
        )
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setStretchLastSection(False)
        self._table.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self._table)

        row = QHBoxLayout()
        add_btn = QPushButton(self.tr("+ Add term"))
        add_btn.clicked.connect(self._on_add)
        row.addWidget(add_btn)
        del_btn = QPushButton(self.tr("Delete selected"))
        del_btn.clicked.connect(self._on_delete)
        row.addWidget(del_btn)
        row.addStretch(1)
        imp_btn = QPushButton(self.tr("Import JSON…"))
        imp_btn.clicked.connect(self._on_import)
        row.addWidget(imp_btn)
        exp_btn = QPushButton(self.tr("Export JSON…"))
        exp_btn.clicked.connect(self._on_export)
        row.addWidget(exp_btn)
        refresh_btn = QPushButton(self.tr("Refresh"))
        refresh_btn.clicked.connect(self.refresh)
        row.addWidget(refresh_btn)
        layout.addLayout(row)

        self._status = QLabel("")
        self._status.setStyleSheet("color: #888;")
        layout.addWidget(self._status)

        self._terms: list[dict[str, Any]] = []
        # Defer the first refresh to _on_sidebar_changed: the backend
        # subprocess starts asynchronously and is not yet ready here.

    # ----- backend I/O -----

    def refresh(self) -> None:
        self._status.setText("")
        try:
            data = self._client.get("/lexicon", timeout=5.0) or {"terms": []}
        except BackendError as exc:
            self._status.setText(
                self.tr("Backend unavailable: {err}").format(err=exc)
            )
            return
        self._terms = list(data.get("terms") or [])
        self._populate()
        self._status.setText(self.tr("{n} term(s)").format(n=len(self._terms)))

    def _populate(self) -> None:
        self._table.blockSignals(True)
        self._table.setRowCount(0)
        for t in self._terms:
            r = self._table.rowCount()
            self._table.insertRow(r)
            self._table.setItem(r, 0, QTableWidgetItem(t.get("source", "")))
            self._table.setItem(r, 1, QTableWidgetItem(t.get("target", "")))
            self._table.setItem(r, 2, QTableWidgetItem(t.get("category") or ""))
            self._table.setItem(r, 3, QTableWidgetItem(t.get("gender") or "unknown"))
            try:
                conf = float(t.get("confidence", 0.5))
            except (TypeError, ValueError):
                conf = 0.5
            conf_item = QTableWidgetItem(f"{conf:.2f}")
            conf_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(r, 4, conf_item)
            self._table.item(r, 0).setData(Qt.ItemDataRole.UserRole, t.get("id"))
        self._table.blockSignals(False)

    # ----- actions -----

    def _on_add(self) -> None:
        r = self._table.rowCount()
        self._table.insertRow(r)
        self._table.setItem(r, 0, QTableWidgetItem(""))
        self._table.setItem(r, 1, QTableWidgetItem(""))
        self._table.setItem(r, 2, QTableWidgetItem("other"))
        self._table.setItem(r, 3, QTableWidgetItem("unknown"))
        self._table.setItem(r, 4, QTableWidgetItem("0.50"))
        self._table.editItem(self._table.item(r, 0))

    def _on_delete(self) -> None:
        rows = sorted({i.row() for i in self._table.selectedItems()}, reverse=True)
        if not rows:
            return
        reply = QMessageBox.question(
            self,
            self.tr("Delete term"),
            self.tr("Delete {n} term(s) permanently? This cannot be undone.").format(
                n=len(rows)
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        for r in rows:
            term_id = self._table.item(r, 0).data(Qt.ItemDataRole.UserRole)
            if term_id:
                try:
                    self._client.delete(f"/lexicon/{term_id}", timeout=5.0)
                except BackendError as exc:
                    QMessageBox.warning(
                        self, self.tr("Delete failed"), str(exc)
                    )
                    return
            self._table.removeRow(r)
        self.refresh()

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        term_id = self._table.item(item.row(), 0).data(Qt.ItemDataRole.UserRole)
        if not term_id:
            # New row being filled in. Persist on first full row.
            self._persist_new_row(item.row())
            return
        col = item.column()
        updates: dict[str, Any] = {}
        if col == 0:
            updates["source"] = item.text().strip()
        elif col == 1:
            updates["target"] = item.text().strip()
        elif col == 2:
            updates["category"] = item.text().strip()
        elif col == 3:
            updates["gender"] = item.text().strip() or "unknown"
        elif col == 4:
            try:
                updates["confidence"] = float(item.text().strip() or "0.5")
            except ValueError:
                updates["confidence"] = 0.5
        if not updates:
            return
        try:
            self._client.put(f"/lexicon/{term_id}", body=updates, timeout=5.0)
        except BackendError as exc:
            self._status.setText(
                self.tr("Update failed: {err}").format(err=exc)
            )

    def _persist_new_row(self, row: int) -> None:
        src = (self._table.item(row, 0) or QTableWidgetItem("")).text().strip()
        tgt = (self._table.item(row, 1) or QTableWidgetItem("")).text().strip()
        if not (src and tgt):
            return
        body = {
            "source": src,
            "target": tgt,
            "category": (self._table.item(row, 2) or QTableWidgetItem("other")).text().strip() or "other",
            "gender": (self._table.item(row, 3) or QTableWidgetItem("unknown")).text().strip() or "unknown",
            "confidence": 0.5,
        }
        try:
            conf_text = (self._table.item(row, 4) or QTableWidgetItem("0.5")).text().strip()
            body["confidence"] = float(conf_text or "0.5")
        except ValueError:
            body["confidence"] = 0.5
        try:
            res = self._client.post("/lexicon", body=body, timeout=5.0)
        except BackendError as exc:
            self._status.setText(self.tr("Add failed: {err}").format(err=exc))
            return
        new_id = (res or {}).get("id")
        if new_id:
            self._table.item(row, 0).setData(Qt.ItemDataRole.UserRole, new_id)
        self.refresh()

    def _apply_filter(self, text: str) -> None:
        text = text.lower().strip()
        for r in range(self._table.rowCount()):
            visible = True
            if text:
                row_text = " ".join(
                    (self._table.item(r, c) or QTableWidgetItem("")).text().lower()
                    for c in range(self._table.columnCount())
                )
                visible = text in row_text
            self._table.setRowHidden(r, not visible)

    def _on_import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, self.tr("Import lexicon"), "", self.tr("JSON (*.json)")
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            QMessageBox.warning(self, self.tr("Import failed"), str(exc))
            return
        terms = data.get("terms") if isinstance(data, dict) else data
        if not isinstance(terms, list):
            QMessageBox.warning(
                self,
                self.tr("Import failed"),
                self.tr("Expected a list or {terms: [...]}."),
            )
            return
        try:
            res = self._client.post("/lexicon/import", body={"terms": terms}, timeout=15.0)
        except BackendError as exc:
            QMessageBox.warning(self, self.tr("Import failed"), str(exc))
            return
        self._status.setText(self.tr("Imported {n} terms.").format(n=res.get("imported", 0)))
        self.refresh()

    def _on_export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Export lexicon"), "lexicon.json", self.tr("JSON (*.json)")
        )
        if not path:
            return
        try:
            data = self._client.get("/lexicon/export", timeout=5.0)
        except BackendError as exc:
            QMessageBox.warning(self, self.tr("Export failed"), str(exc))
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            QMessageBox.warning(self, self.tr("Export failed"), str(exc))
            return
        self._status.setText(self.tr("Exported to {path}").format(path=path))


__all__ = ["GlossariesTab"]
