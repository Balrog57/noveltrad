"""DashboardTab — Main landing page for NovelTrad.

Shows welcome message, quick actions, pipeline visualization (if active),
recent projects, and system status.
"""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..widgets.pipeline_visualization import (
    DashboardQuickActions,
    PipelineVisualization,
)


class DashboardTab(QWidget):
    """Landing page shown when NovelTrad starts."""

    openFileRequested = pyqtSignal()
    openProjectsRequested = pyqtSignal()
    openGlossariesRequested = pyqtSignal()
    openSettingsRequested = pyqtSignal()
    navigateTo = pyqtSignal(str)  # key in SIDEBAR_ITEMS

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._last_state: dict[str, Any] = {}

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 20, 24, 20)

        # --- Welcome ---
        welcome = QLabel(self.tr(
            "Bienvenue sur NovelTrad\n\n"
            "Traduisez vos livres (EPUB, TXT, DOCX, SRT) "
            "via une pipeline IA à 11 étapes.\n"
            "Glossaire automatique, correcteur grammatical, "
            "boucle réflexive — le tout en local."
        ))
        welcome.setWordWrap(True)
        welcome.setStyleSheet("font-size: 14pt; color: #555; padding: 8px 0;")
        layout.addWidget(welcome)

        # --- Quick actions ---
        actions = DashboardQuickActions()
        actions.openFileRequested.connect(self.openFileRequested.emit)
        actions.openProjectsRequested.connect(
            lambda: self.navigateTo.emit("projects")
        )
        actions.openGlossariesRequested.connect(
            lambda: self.navigateTo.emit("glossaries")
        )
        layout.addWidget(actions)

        # --- Pipeline viz (hidden when idle) ---
        self._pipeline_viz = PipelineVisualization()
        self._pipeline_viz.setVisible(False)
        layout.addWidget(self._pipeline_viz)

        # --- Status row ---
        status_row = QHBoxLayout()
        status_row.setSpacing(20)

        self._backend_status = QLabel(self.tr("🔴 Backend: …"))
        self._backend_status.setStyleSheet(
            "padding: 6px 12px; border: 1px solid #ddd; "
            "border-radius: 6px; font-size: 10pt;"
        )
        status_row.addWidget(self._backend_status)
        self._llm_status = QLabel(self.tr("🤖 LLM: …"))
        self._llm_status.setStyleSheet(
            "padding: 6px 12px; border: 1px solid #ddd; "
            "border-radius: 6px; font-size: 10pt;"
        )
        status_row.addWidget(self._llm_status)
        status_row.addStretch(1)
        layout.addLayout(status_row)

        # --- Recent projects (compact table) ---
        recent_label = QLabel(self.tr("📁  Projets récents"))
        recent_label.setStyleSheet("font-weight: 600; font-size: 12pt;")
        layout.addWidget(recent_label)

        self._recent_table = QTableWidget(0, 3)
        self._recent_table.setHorizontalHeaderLabels([
            self.tr("Fichier source"),
            self.tr("Langue"),
            self.tr("Date"),
        ])
        self._recent_table.verticalHeader().setVisible(False)
        self._recent_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self._recent_table.setSelectionMode(
            QTableWidget.SelectionMode.NoSelection
        )
        self._recent_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._recent_table.setAlternatingRowColors(True)
        hh = self._recent_table.horizontalHeader()
        hh.setStretchLastSection(True)
        hh.setSectionResizeMode(0, hh.ResizeMode.Stretch)
        layout.addWidget(self._recent_table, 1)

        # --- Footer ---
        footer = QLabel(
            self.tr("Astuce : déposez un fichier EPUB/TXT/DOCX/SRT "
                    "sur la fenêtre ou utilisez Ctrl+O pour commencer.")
        )
        footer.setStyleSheet("color: #999; font-size: 9pt; padding: 8px 0;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer)

    def update_pipeline_state(self, state: dict[str, Any]) -> None:
        """Refresh pipeline viz and status from /pipeline/state."""
        self._last_state = state
        project = state.get("project") or {}
        ss = state.get("state_store") or {}

        # Backend status
        ok = state.get("ok", False)
        self._backend_status.setText(
            self.tr("🟢 Backend OK") if ok else self.tr("🔴 Backend: démarrage…")
        )

        # LLM
        llm_info = state.get("llm", {})
        mode = llm_info.get("mode", "?")
        provider = llm_info.get("usage", {}).get("primary", "?")
        self._llm_status.setText(
            self.tr(f"🤖 LLM: {provider} ({mode})")
        )

        # Pipeline viz
        active_stage = project.get("current_stage")
        chunks_total = ss.get("chunks_total", 0)
        chunks_by_status = ss.get("chunks_by_status", {})
        lexicon_count = len(state.get("lexicon", []))

        if active_stage or chunks_total:
            self._pipeline_viz.setVisible(True)
            self._pipeline_viz.set_state(
                active_stage, chunks_total,
                chunks_by_status, lexicon_count
            )
        else:
            self._pipeline_viz.setVisible(False)

    def set_recent_projects(self, projects: list[dict[str, Any]]) -> None:
        """Populate the recent projects table."""
        self._recent_table.setRowCount(0)
        for proj in projects[-20:]:  # keep last 20
            row = self._recent_table.rowCount()
            self._recent_table.insertRow(row)
            self._recent_table.setItem(
                row, 0,
                QTableWidgetItem(proj.get("source_path", "-"))
            )
            self._recent_table.setItem(
                row, 1,
                QTableWidgetItem(
                    f"{proj.get('source_lang', '?')} → "
                    f"{proj.get('target_lang', '?')}"
                )
            )
            self._recent_table.setItem(
                row, 2,
                QTableWidgetItem(proj.get("created_at", "-"))
            )
