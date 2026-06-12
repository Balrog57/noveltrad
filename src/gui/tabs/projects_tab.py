"""Projects tab — lists past translation projects with re-open action."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class ProjectsTab(QWidget):
    projectActivated = pyqtSignal(dict)

    def __init__(self, client, parent=None):
        super().__init__(parent)
        self._client = client
        self._projects: list[dict] = []

        layout = QVBoxLayout(self)
        title = QLabel(self.tr("Recent projects"))
        title.setProperty("role", "title")
        layout.addWidget(title)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels([
            self.tr("Source"),
            self.tr("Languages"),
            self.tr("Profile"),
            self.tr("Date"),
            self.tr("Open"),
        ])
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setStretchLastSection(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        layout.addWidget(self._table, 1)

        self._status = QLabel("")
        self._status.setProperty("role", "muted")
        layout.addWidget(self._status)

        btn = QPushButton(self.tr("Refresh"))
        btn.clicked.connect(self.refresh)
        layout.addWidget(btn)

    def refresh(self) -> None:
        self._status.setText("")
        try:
            data = self._client.get("/projects", timeout=5.0) or {}
            items = data.get("projects") or []
        except Exception as exc:
            self._status.setText(self.tr("Failed to load: {err}").format(err=exc))
            return
        self._projects = items
        self._table.setRowCount(len(items))
        for row_idx, proj in enumerate(items):
            src = proj.get("source_path", "")
            try:
                from pathlib import Path
                src_name = Path(src).name
            except Exception:
                src_name = src
            langs = f"{proj.get('source_lang', '?')} → {proj.get('target_lang', '?')}"
            profile = proj.get("profile", "balanced").capitalize()
            created = proj.get("created_at", "")[:10]
            self._table.setItem(row_idx, 0, QTableWidgetItem(src_name))
            self._table.setItem(row_idx, 1, QTableWidgetItem(langs))
            self._table.setItem(row_idx, 2, QTableWidgetItem(profile))
            self._table.setItem(row_idx, 3, QTableWidgetItem(created))
            open_btn = QPushButton(self.tr("Open"))
            open_btn.clicked.connect(lambda checked, p=proj: self.projectActivated.emit(p))
            self._table.setCellWidget(row_idx, 4, open_btn)
        self._status.setText(self.tr("{n} project(s)").format(n=len(items)))

    def _on_cell_double_clicked(self, row: int, _col: int) -> None:
        if 0 <= row < len(self._projects):
            self.projectActivated.emit(self._projects[row])
