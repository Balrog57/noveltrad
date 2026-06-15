"""PipelineVisualization — live 11-stage flow display.

Shows each pipeline stage as a card with icon, name, status indicator,
and progress bar. Updates are driven by /pipeline/state data.
"""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

STAGE_ICONS: dict[str, str] = {
    "parser":                "📖 Parser",
    "fast_translator":       "🌐 Fast Translator",
    "lexicon_builder":       "📝 Lexicon Builder",
    "terminology_researcher":"🔬 Term. Researcher",
    "glossary_applier":      "📋 Glossary Applier",
    "consistency_checker":   "✅ Consistency Checker",
    "qa_validator":          "🔍 QA Validator",
    "grammar_proofer":       "📐 Grammar Proofer",
    "reviewer":              "⭐ Reviewer",
    "llm_polisher":          "✨ LLM Polisher",
    "assembler":             "📦 Assembler",
}

STAGE_ORDER = list(STAGE_ICONS.keys())


def _status_emoji(status: str | None) -> str:
    return {
        "running": "🔄",
        "done":    "✅",
        "error":   "❌",
        "pending": "⏳",
        "skipped": "⏭️",
    }.get(status or "pending", "⏳")


class _StageCard(QFrame):
    """Single stage card: icon + name + status + optional progress."""

    clicked = pyqtSignal(str)

    def __init__(self, stage_key: str, parent: QWidget | None = None):
        super().__init__(parent)
        self._stage_key = stage_key
        label = STAGE_ICONS.get(stage_key, stage_key)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(stage_key)

        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(8, 6, 8, 6)

        self._emoji = QLabel("⏳")
        self._emoji.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = self._emoji.font()
        font.setPointSize(16)
        self._emoji.setFont(font)
        layout.addWidget(self._emoji)

        name = QLabel(label)
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name.setWordWrap(True)
        name.setStyleSheet("font-size: 10pt;")
        layout.addWidget(name)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setFixedHeight(6)
        self._bar.setTextVisible(False)
        layout.addWidget(self._bar)

        self._count_label = QLabel("")
        self._count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._count_label.setStyleSheet("font-size: 8pt; color: gray;")
        layout.addWidget(self._count_label)

    def mousePressEvent(self, event) -> None:  # noqa: ANN001
        self.clicked.emit(self._stage_key)
        super().mousePressEvent(event)

    def set_status(self, status: str | None, progress: int = 0,
                   count: str = "") -> None:
        self._emoji.setText(_status_emoji(status))
        color = {
            "running": "#2196F3",
            "done":    "#4CAF50",
            "error":   "#f44336",
            "pending": "#9e9e9e",
            "skipped": "#607d8b",
        }.get(status or "pending", "#9e9e9e")
        self.setStyleSheet(f"border: 1px solid {color}; border-radius: 6px; "
                           f"background: {color}15;")
        self._bar.setValue(progress)
        self._count_label.setText(count)


class PipelineVisualization(QScrollArea):
    """Horizontal scrolling display of all 11 pipeline stages."""

    stageClicked = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.setFixedHeight(110)

        container = QWidget()
        self._layout = QHBoxLayout(container)
        self._layout.setSpacing(6)
        self._layout.setContentsMargins(8, 4, 8, 4)

        self._cards: dict[str, _StageCard] = {}
        for stage in STAGE_ORDER:
            card = _StageCard(stage)
            card.clicked.connect(self.stageClicked.emit)
            self._cards[stage] = card
            self._layout.addWidget(card)

        self._layout.addStretch(1)
        self.setWidget(container)

        # Default: all pending
        self.set_state(None, None, None, 0)

    def set_state(self, active_stage: str | None,
                  chunks_total: int | None,
                  chunks_by_status: dict[str, int] | None,
                  lexicon_count: int = 0) -> None:
        """Update cards from pipeline state data."""
        done_stages: set[str] = set()
        current_idx = -1
        if active_stage and active_stage in self._cards:
            try:
                current_idx = STAGE_ORDER.index(active_stage)
            except ValueError:
                pass
        if current_idx >= 0:
            done_stages = set(STAGE_ORDER[:current_idx])

        for i, stage in enumerate(STAGE_ORDER):
            if current_idx >= 0 and i < current_idx:
                st = "done"
            elif stage == active_stage:
                st = "running"
            else:
                st = "pending"

            progress = 0
            count = ""
            if chunks_total and chunks_by_status:
                statuses = {
                    "done":    chunks_by_status.get("polished", 0),
                    "running": chunks_by_status.get("processing", 0),
                    "pending": chunks_by_status.get("pending", 0),
                    "error":   chunks_by_status.get("error", 0),
                }
                total_done = statuses["done"] + statuses["error"]

                if stage == "parser" and chunks_total:
                    progress = min(100, int(100 * total_done / max(1, chunks_total)))
                elif stage == "assembler" and \
                        chunks_by_status.get("assembled", 0) > 0:
                    progress = 100
                elif stage == active_stage and chunks_total:
                    progress = min(100, int(100 * total_done / max(1, chunks_total)))
                else:
                    progress = 100 if st == "done" else 0

                if stage == "lexicon_builder" and lexicon_count:
                    count = f"{lexicon_count} terms"

            self._cards[stage].set_status(st, progress, count)


class DashboardQuickActions(QFrame):
    """Quick action buttons for the dashboard."""

    openFileRequested = pyqtSignal()
    openProjectsRequested = pyqtSignal()
    openGlossariesRequested = pyqtSignal()
    openSettingsRequested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QHBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 12, 16, 12)

        self._open_btn = self._btn("📂  Open file", "Ctrl+O")
        self._projects_btn = self._btn("📁  Projects")
        self._glossary_btn = self._btn("📖  Glossaries")
        self._settings_btn = self._btn("⚙  Settings", "Ctrl+,")

        self._open_btn.clicked.connect(self.openFileRequested.emit)
        self._projects_btn.clicked.connect(self.openProjectsRequested.emit)
        self._glossary_btn.clicked.connect(self.openGlossariesRequested.emit)
        self._settings_btn.clicked.connect(self.openSettingsRequested.emit)

        layout.addWidget(self._open_btn)
        layout.addWidget(self._projects_btn)
        layout.addWidget(self._glossary_btn)
        layout.addStretch(1)

    def _btn(self, text: str, shortcut: str = "") -> QPushButton:
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            "padding: 10px 16px; border: 1px solid #ccc; "
            "border-radius: 8px; font-weight: 600; font-size: 11pt;"
        )
        if shortcut:
            btn.setToolTip(f"Shortcut: {shortcut}")
        return btn
