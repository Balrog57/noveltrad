"""Files tab — file explorer for the active project directory.

Shows all files in the project folder with their translation status
(working / done / error / queued). Double-click opens the file in the
default system editor for preview/correction.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.gui.a11y import configure
from src.gui.backend_client import BackendClient, BackendError


# Mapping from chunk statuses to emoji indicators.
STATUS_ICONS: dict[str, str] = {
    "done": "✅",
    "polished": "✅",
    "assembled": "✅",
    "parsed": "🔄",
    "fast_translated": "🔄",
    "lexicon_ready": "🔄",
    "glossary_applied": "🔄",
    "consistency_checked": "🔄",
    "qa_checked": "🔄",
    "grammar_checked": "🔄",
    "reviewed": "🔄",
    "error": "❌",
    "hash_mismatch": "⚠️",
    "waiting_for_human": "⏸️",
}

STATUS_GROUPS: dict[str, str] = {
    "done": "Done",
    "polished": "Done",
    "assembled": "Done",
    "parsed": "Working",
    "fast_translated": "Working",
    "lexicon_ready": "Working",
    "glossary_applied": "Working",
    "consistency_checked": "Working",
    "qa_checked": "Working",
    "grammar_checked": "Working",
    "reviewed": "Working",
    "error": "Error",
    "hash_mismatch": "Error",
    "waiting_for_human": "Paused",
}

FILTER_OPTIONS = ["All", "Done", "Working", "Error", "Paused"]


class FilesTab(QWidget):
    chunkActivated = pyqtSignal(str)  # chunk_id (kept for backward compat)
    fileOpened = pyqtSignal(str)  # file path

    def __init__(self, client: BackendClient, parent: QWidget | None = None):
        super().__init__(parent)
        self._client = client
        self._project: dict[str, Any] | None = None
        self._file_statuses: dict[str, str] = {}  # path → status_group

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # Header.
        header_row = QHBoxLayout()
        self._title = QLabel(self.tr("📁 Fichiers"))
        self._title.setProperty("role", "title")
        header_row.addWidget(self._title)
        header_row.addStretch(1)

        filter_label = QLabel(self.tr("Filtre:"))
        header_row.addWidget(filter_label)
        self._status_filter = QComboBox()
        for opt in FILTER_OPTIONS:
            self._status_filter.addItem(self.tr(opt), opt)
        self._status_filter.currentIndexChanged.connect(self._apply_filter)
        header_row.addWidget(self._status_filter)
        layout.addLayout(header_row)

        # Folder path.
        self._folder_label = QLabel("")
        self._folder_label.setProperty("role", "muted")
        layout.addWidget(self._folder_label)

        # File table: Name, Status, Size, Actions.
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels([
            self.tr("Fichier"),
            self.tr("Statut"),
            self.tr("Taille"),
            self.tr("Actions"),
        ])
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setStretchLastSection(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.cellDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self._table, 1)

        # Status bar.
        self._status = QLabel("")
        self._status.setProperty("role", "muted")
        layout.addWidget(self._status)

    def set_project(self, proj: dict[str, Any]) -> None:
        """Set the active project and refresh the file list."""
        self._project = proj
        self._title.setText(
            self.tr("📁 Fichiers — {name}").format(
                name=proj.get("name", proj.get("project_id", "?")[:8])
            )
        )
        self.refresh()

    def refresh(self) -> None:
        self._table.setRowCount(0)
        self._status.setText("")
        if self._project is None:
            self._folder_label.setText(self.tr("Aucun projet actif."))
            self._status.setText(self.tr("Sélectionnez un projet d'abord."))
            return

        project_dir = self._project.get("project_dir", "")
        self._folder_label.setText(
            self.tr("Dossier: {dir}").format(dir=project_dir)
        )

        # Fetch chunk statuses from the backend.
        self._file_statuses = {}
        try:
            data = self._client.get("/chunks", params={"limit": 500}, timeout=5.0) or {}
            chunks = data.get("chunks") or data.get("items") or []
            for c in chunks:
                src_file = c.get("source_file", "")
                if src_file:
                    fname = Path(src_file).name
                    status = c.get("status", "parsed")
                    group = STATUS_GROUPS.get(status, "Working")
                    # Only upgrade: don't downgrade a done file to working.
                    current = self._file_statuses.get(fname)
                    if current is None or (group == "Done" and current != "Done"):
                        self._file_statuses[fname] = group
        except BackendError:
            pass

        # Scan the project directory.
        all_files: list[Path] = []
        try:
            root = Path(project_dir)
            if root.is_dir():
                all_files = sorted(
                    [f for f in root.iterdir() if f.is_file()],
                    key=lambda f: f.stat().st_mtime,
                    reverse=True,
                )
        except OSError:
            self._status.setText(self.tr("Dossier inaccessible."))
            return

        # Also include source files tracked in the DB but not on disk.
        db_files = set(self._file_statuses.keys())
        disk_files = {f.name for f in all_files}

        # Map status group for display.
        filter_group = self._status_filter.currentData()

        row = 0
        for filepath in all_files:
            fname = filepath.name
            status_group = self._file_statuses.get(fname, "")
            # Determine emoji + label.
            if status_group == "Done":
                icon = "✅"
                label = self.tr("Terminé")
            elif status_group == "Error":
                icon = "❌"
                label = self.tr("Erreur")
            elif status_group == "Paused":
                icon = "⏸️"
                label = self.tr("En pause")
            elif status_group == "Working":
                icon = "🔄"
                label = self.tr("En cours")
            else:
                # File not tracked by backend — show as untranslated.
                icon = "📄"
                label = self.tr("Non traduit")

            if filter_group and filter_group != "All":
                display_group = status_group or "Untranslated"
                if filter_group == "Error":
                    if status_group != "Error":
                        continue
                elif filter_group == "Paused":
                    if status_group != "Paused":
                        continue
                elif display_group not in (filter_group,):
                    continue

            try:
                size_bytes = filepath.stat().st_size
            except OSError:
                size_bytes = 0
            size_str = _format_size(size_bytes)

            self._table.insertRow(row)
            self._table.setItem(row, 0, QTableWidgetItem(fname))
            self._table.item(row, 0).setData(Qt.ItemDataRole.UserRole, str(filepath))
            self._table.setItem(row, 1, QTableWidgetItem(f"{icon} {label}"))
            self._table.setItem(row, 2, QTableWidgetItem(size_str))

            # Action buttons.
            action_widget = QWidget()
            action_row = QHBoxLayout(action_widget)
            action_row.setContentsMargins(0, 0, 0, 0)
            action_row.setSpacing(4)

            view_btn = QPushButton(self.tr("👁 Voir"))
            view_btn.clicked.connect(lambda checked, fp=str(filepath): self._open_file(fp))
            configure(view_btn, name=self.tr("Voir {fname}").format(fname=fname))
            action_row.addWidget(view_btn)

            retry_btn = QPushButton(self.tr("🔄 Réessayer"))
            retry_btn.setToolTip(self.tr("Relancer la traduction pour ce fichier"))
            retry_btn.clicked.connect(lambda checked, fp=str(filepath): self._retry_file(fp))
            configure(retry_btn, name=self.tr("Réessayer {fname}").format(fname=fname))
            action_row.addWidget(retry_btn)

            self._table.setCellWidget(row, 3, action_widget)
            row += 1

        # Count statuses.
        counts: dict[str, int] = {}
        for group in self._file_statuses.values():
            counts[group] = counts.get(group, 0) + 1
        parts = [f"{len(all_files)} fichiers"]
        if counts:
            details = ", ".join(f"{v} {k.lower()}" for k, v in sorted(counts.items()))
            parts.append(details)
        self._status.setText(" · ".join(parts))

    def _apply_filter(self) -> None:
        self.refresh()

    def _open_file(self, filepath: str) -> None:
        """Open the file in the default system editor."""
        try:
            os.startfile(filepath)
            self.fileOpened.emit(filepath)
        except OSError as exc:
            QMessageBox.warning(
                self,
                self.tr("Erreur"),
                self.tr("Impossible d'ouvrir: {err}").format(err=exc),
            )

    def _retry_file(self, filepath: str) -> None:
        """Re-inject the file for translation."""
        fname = Path(filepath).name
        try:
            # Find chunk IDs for this file.
            data = self._client.get(
                "/chunks",
                params={"limit": 500},
                timeout=5.0,
            ) or {}
            chunks = data.get("chunks") or data.get("items") or []
            chunk_ids = [
                c["id"] for c in chunks
                if Path(c.get("source_file", "")).name == fname
            ]
            if not chunk_ids:
                self._status.setText(
                    self.tr("Aucun chunk trouvé pour {f}").format(f=fname)
                )
                return
            res = self._client.post(
                "/pipeline/replay-chunks",
                body={"chunk_ids": chunk_ids},
                timeout=10.0,
            ) or {}
            replayed = res.get("replayed", 0)
            self._status.setText(
                self.tr("{n} chunk(s) relancé(s) pour {f}").format(
                    n=replayed, f=fname
                )
            )
            self.refresh()
        except BackendError as exc:
            self._status.setText(
                self.tr("Échec: {err}").format(err=exc)
            )

    def _on_double_click(self, row: int, col: int) -> None:
        item = self._table.item(row, 0)
        if item is None:
            return
        filepath = item.data(Qt.ItemDataRole.UserRole)
        if filepath:
            self._open_file(str(filepath))


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


__all__ = ["FilesTab"]
