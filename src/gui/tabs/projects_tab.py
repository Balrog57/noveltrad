"""Projects tab — project hub: history, CRUD, activation.

Layout:
    [+ New] [📂 Open folder]
    ┌──────────────────────────────────────┐
    │ 🔵 Project name     C:/path/         │
    │    120 files · 2h ago  [Open] [✏ Rename] [🗑] │
    │ ⚪ Another project    C:/other/       │
    │    45 files · 3d ago   [Open] [✏ Rename] [🗑] │
    └──────────────────────────────────────┘
    Active: 🔵 Project name
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.gui.backend_client import BackendClient, BackendError
from src.gui.dialogs.project_dialog import ProjectDialog


class ProjectsTab(QWidget):
    projectActivated = pyqtSignal(dict)

    def __init__(self, client: BackendClient, parent: QWidget | None = None):
        super().__init__(parent)
        self._client = client
        self._projects: list[dict[str, Any]] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # Header row: title + action buttons.
        header = QHBoxLayout()
        title = QLabel(self.tr("📁 Projects"))
        title.setProperty("role", "title")
        header.addWidget(title)
        header.addStretch(1)
        new_btn = QPushButton(self.tr("+ New"))
        new_btn.setProperty("role", "primary")
        new_btn.clicked.connect(self._on_new)
        header.addWidget(new_btn)
        open_btn = QPushButton(self.tr("📂 Open folder"))
        open_btn.clicked.connect(self._on_open_folder)
        header.addWidget(open_btn)
        layout.addLayout(header)

        # History label.
        history_label = QLabel(self.tr("Historique (10 derniers)"))
        history_label.setProperty("role", "muted")
        layout.addWidget(history_label)

        # Project table: Name, Folder, Info, Actions.
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels([
            self.tr("Nom"),
            self.tr("Dossier"),
            self.tr("Infos"),
            self.tr("Actions"),
        ])
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
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

        # Defer the first refresh to sidebar activation.
        QWidget.setVisible(self, True)

    # ── public API ────────────────────────────────────────────

    def refresh(self) -> None:
        self._status.setText("")
        try:
            data = self._client.get("/projects", params={"limit": 10}, timeout=5.0) or {}
            items = data.get("projects") or []
        except BackendError as exc:
            self._status.setText(self.tr("Erreur: {err}").format(err=exc))
            return
        # Also fetch active project to mark it.
        try:
            active_data = self._client.get("/projects/active", timeout=3.0) or {}
            active_id = active_data.get("active_project_id")
        except BackendError:
            active_id = None

        self._projects = items
        self._table.setRowCount(len(items))
        for row, proj in enumerate(items):
            pid = proj.get("project_id", "")
            name = proj.get("name", f"Project-{pid[:8]}")
            folder = proj.get("project_dir", "")
            is_active = bool(active_id and active_id == pid)
            prefix = "🔵 " if is_active else "⚪ "

            self._table.setItem(row, 0, QTableWidgetItem(prefix + name))
            self._table.setItem(row, 1, QTableWidgetItem(folder))
            self._table.setItem(row, 2, QTableWidgetItem(self._info_text(proj)))

            # Action buttons per row.
            action_widget = QWidget()
            action_row = QHBoxLayout(action_widget)
            action_row.setContentsMargins(0, 0, 0, 0)
            action_row.setSpacing(4)

            open_btn = QPushButton(self.tr("Open"))
            open_btn.clicked.connect(lambda checked, p=proj: self.projectActivated.emit(p))
            action_row.addWidget(open_btn)

            rename_btn = QPushButton(self.tr("✏"))
            rename_btn.setToolTip(self.tr("Renommer"))
            rename_btn.setFixedWidth(30)
            rename_btn.clicked.connect(lambda checked, p=proj: self._on_rename(p))
            action_row.addWidget(rename_btn)

            del_btn = QPushButton(self.tr("🗑"))
            del_btn.setToolTip(self.tr("Supprimer"))
            del_btn.setFixedWidth(30)
            del_btn.clicked.connect(lambda checked, p=proj: self._on_delete(p))
            action_row.addWidget(del_btn)

            self._table.setCellWidget(row, 3, action_widget)

        self._status.setText(
            self.tr("{n} projet(s)").format(n=len(items))
        )

    # ── helpers ───────────────────────────────────────────────

    def _info_text(self, proj: dict[str, Any]) -> str:
        """Build a compact info string for the Info column."""
        folder = proj.get("project_dir", "")
        file_count = "?"
        try:
            project_dir = Path(folder)
            if project_dir.is_dir():
                files = list(project_dir.glob("*"))
                file_count = str(len(files))
        except Exception:
            pass
        created = proj.get("created_at", "")[:10]
        parts = [f"{file_count} fichiers", created] if created else [f"{file_count} fichiers"]
        return " · ".join(parts)

    # ── actions ───────────────────────────────────────────────

    def _on_new(self) -> None:
        dlg = ProjectDialog(self, title=self.tr("Nouveau projet"))
        if dlg.exec() != ProjectDialog.DialogCode.Accepted:
            return
        name = dlg.project_name().strip()
        folder = dlg.project_folder().strip()
        if not name or not folder:
            QMessageBox.warning(self, self.tr("Erreur"), self.tr("Nom et dossier requis."))
            return
        try:
            res = self._client.post(
                "/projects",
                body={"name": name, "project_dir": folder},
                timeout=5.0,
            ) or {}
        except BackendError as exc:
            self._status.setText(self.tr("Échec: {err}").format(err=exc))
            return
        pid = res.get("project_id", "")
        proj = {"project_id": pid, "name": name, "project_dir": folder}
        self.refresh()
        self.projectActivated.emit(proj)

    def _on_open_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, self.tr("Ouvrir un dossier de projet"), str(Path.home())
        )
        if not folder:
            return
        # Extract project name from folder name.
        name = Path(folder).name
        try:
            res = self._client.post(
                "/projects",
                body={"name": name, "project_dir": folder},
                timeout=5.0,
            ) or {}
        except BackendError as exc:
            self._status.setText(self.tr("Échec: {err}").format(err=exc))
            return
        pid = res.get("project_id", "")
        proj = {"project_id": pid, "name": name, "project_dir": folder}
        self.refresh()
        self.projectActivated.emit(proj)

    def _on_rename(self, proj: dict[str, Any]) -> None:
        pid = proj.get("project_id", "")
        old_name = proj.get("name", pid[:8])
        new_name, ok = QInputDialog.getText(
            self,
            self.tr("Renommer"),
            self.tr("Nouveau nom:"),
            text=old_name,
        )
        if not ok or not new_name.strip():
            return
        try:
            self._client.put(
                f"/projects/{pid}",
                body={"name": new_name.strip()},
                timeout=5.0,
            )
        except BackendError as exc:
            self._status.setText(self.tr("Échec: {err}").format(err=exc))
            return
        self.refresh()

    def _on_delete(self, proj: dict[str, Any]) -> None:
        pid = proj.get("project_id", "")
        name = proj.get("name", pid[:8])
        confirm = QMessageBox.question(
            self,
            self.tr("Supprimer le projet"),
            self.tr(
                "Supprimer « {name} » ?\n\n"
                "Le dossier de travail n'est PAS supprimé, "
                "seulement les métadonnées du projet."
            ).format(name=name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            self._client.delete(f"/projects/{pid}", timeout=5.0)
        except BackendError as exc:
            self._status.setText(self.tr("Échec: {err}").format(err=exc))
            return
        self.refresh()

    def _on_double_click(self, row: int, _col: int) -> None:
        if 0 <= row < len(self._projects):
            self.projectActivated.emit(self._projects[row])


__all__ = ["ProjectsTab"]
