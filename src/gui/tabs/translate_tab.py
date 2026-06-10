"""Translate tab — 3-step workflow (Select / Pipeline / Review).

Mirrors the TBL UX. Drops a file → POST /projects → orchestrator
parses and the activity log shows progress. The tab is split into
three pages, switched by the WebSocket event stream:

  0 Select   — drop zone, source/target language, quality preset.
  1 Pipeline — per-stage status cards, pause/resume/stop controls,
               "Re-run" + "Replay pending HITL" actions.
  2 Review   — virtualised list of chunks with status filter, double
               click opens the chunk detail dialog.
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
    QHeaderView,
    QLabel,
    QListView,
    QPushButton,
    QStackedLayout,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..a11y import configure, set_touch_target
from .review_model import ChunkReviewModel

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

PIPELINE_STAGES: tuple[str, ...] = (
    "parser",
    "fast_translator",
    "lexicon_builder",
    "glossary_applier",
    "consistency_checker",
    "qa_validator",
    "grammar_proofer",
    "llm_polisher",
    "assembler",
)


class _DropZone(QFrame):
    fileDropped = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setProperty("role", "dropzone")
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
        self._sub.setProperty("role", "muted")
        layout.addWidget(self._sub)
        self._browse = QPushButton("Browse Files")
        self._browse.setProperty("role", "primary")
        self._browse.clicked.connect(self._open_dialog)
        layout.addWidget(self._browse, alignment=Qt.AlignmentFlag.AlignCenter)
        self._path_label = QLabel("")
        self._path_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._path_label.setWordWrap(True)
        layout.addWidget(self._path_label)
        self._dropped: str | None = None

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setProperty("active", "true")
            self.style().unpolish(self)
            self.style().polish(self)

    def dragLeaveEvent(self, event) -> None:  # noqa: ANN001 - Qt signature
        self.setProperty("active", "false")
        self.style().unpolish(self)
        self.style().polish(self)
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        self.setProperty("active", "false")
        self.style().unpolish(self)
        self.style().polish(self)
        if not urls:
            return
        local = urls[0].toLocalFile()
        if local:
            self.set_path(local)
            self.fileDropped.emit(local)
            event.acceptProposedAction()

    def mousePressEvent(self, event) -> None:  # noqa: ANN001 - Qt signature
        if event.button() == Qt.MouseButton.LeftButton:
            self._open_dialog()
        super().mousePressEvent(event)

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

    def selected_path(self) -> str | None:
        return self._dropped


class TranslateTab(QWidget):
    startRequested = pyqtSignal(dict)
    fileSelected = pyqtSignal(str)
    replayHltlRequested = pyqtSignal()
    assembleRequested = pyqtSignal(str)  # format

    def __init__(
        self,
        parent: QWidget | None = None,
        default_target: str = "fr",
        client: Any = None,
    ):
        super().__init__(parent)
        self._client = client
        self._selected_path: str | None = None
        self._project_dir: str = ""

        # Outer layout = vertical stack: header bar + stacked pages.
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Sticky header.
        self._header = QWidget()
        hlayout = QHBoxLayout(self._header)
        hlayout.setContentsMargins(16, 10, 16, 10)
        self._step_label = QLabel("1 · Select")
        self._step_label.setProperty("role", "title")
        hlayout.addWidget(self._step_label)
        hlayout.addStretch(1)
        self._progress_label = QLabel("")
        self._progress_label.setProperty("role", "muted")
        hlayout.addWidget(self._progress_label)
        outer.addWidget(self._header)

        self._stack = QStackedLayout()
        outer.addLayout(self._stack, 1)

        # Page 0: Select.
        self._select_page = self._build_select_page(default_target)
        self._stack.addWidget(self._select_page)

        # Page 1: Pipeline.
        self._pipeline_page = self._build_pipeline_page()
        self._stack.addWidget(self._pipeline_page)

        # Page 2: Review.
        self._review_page = self._build_review_page()
        self._stack.addWidget(self._review_page)

    # ----- public API -----

    def set_client(self, client: Any) -> None:
        self._client = client
        if self._review_model is not None:
            self._review_model._client = client  # type: ignore[attr-defined]

    def set_project_dir(self, project_dir: str) -> None:
        self._project_dir = project_dir

    def set_status(self, text: str) -> None:
        self._progress_label.setText(text)

    def go_to_step(self, step: int) -> None:
        if 0 <= step < self._stack.count():
            self._stack.setCurrentIndex(step)
            labels = ["1 · Select", "2 · Pipeline", "3 · Review"]
            self._step_label.setText(labels[step])

    def update_pipeline_state(self, state: dict[str, Any]) -> None:
        """Refresh the pipeline page from /pipeline/state JSON."""
        ss = state.get("state_store") or {}
        counts = ss.get("chunks_by_status") or {}
        total = ss.get("chunks_total") or 0
        for stage, row in self._stage_rows.items():
            count = counts.get(stage, 0) or counts.get(self._status_alias(stage), 0)
            row["count"].setText(f"{count} chunks")
            row["progress"].setValue(min(100, int(100 * count / max(1, total))))
        polished = counts.get("polished", 0)
        issues = (
            ss.get("qa_issues", 0)
            + ss.get("grammar_issues", 0)
            + ss.get("consistency_flags", 0)
        )
        if total:
            self._progress_label.setText(
                f"{polished}/{total} chunks · {issues} issues"
            )
        artifact = state.get("output_artifact") or {}
        if artifact.get("output_path"):
            self._assemble_btn.setEnabled(True)
            self._assemble_btn.setText("📦  Open output folder")
        if any(counts.values()):
            self.go_to_step(1)

    def on_artifact_ready(self, output_path: str) -> None:
        self._assemble_btn.setEnabled(True)
        self._assemble_btn.setText("📦  Open output folder")
        self._progress_label.setText(f"Done · {output_path}")
        # Refresh review list and switch to it.
        if self._review_model is not None:
            self._review_model.refresh()
        self.go_to_step(2)

    # ----- builders -----

    def _build_select_page(self, default_target: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        lang_row = QHBoxLayout()
        lang_row.addWidget(QLabel("SOURCE LANG"))
        self._src = QComboBox()
        for code, label in LANGUAGES:
            self._src.addItem(label, code)
        configure(self._src, name="Source language")
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
        configure(self._tgt, name="Target language")
        lang_row.addWidget(self._tgt, 1)
        layout.addLayout(lang_row)

        # Quality preset selector.
        quality_row = QHBoxLayout()
        quality_row.addWidget(QLabel("QUALITY"))
        self._quality = QComboBox()
        self._quality.addItem("Fast (skip polish + grammar)", "fast")
        self._quality.addItem("Balanced (default)", "balanced")
        self._quality.addItem("High (full QA + double-pass polish)", "high")
        configure(self._quality, name="Quality preset")
        quality_row.addWidget(self._quality, 1)
        layout.addLayout(quality_row)

        self._drop = _DropZone()
        self._drop.fileDropped.connect(self._on_file)
        layout.addWidget(self._drop, 1)

        self._start_btn = QPushButton("▶  Start Translation")
        self._start_btn.setProperty("role", "primary")
        set_touch_target(self._start_btn, 48)
        self._start_btn.setEnabled(False)
        self._start_btn.clicked.connect(self._on_start)
        configure(
            self._start_btn,
            name="Start translation",
            description="Kick off the multi-agent translation pipeline.",
            shortcut="Ctrl+Return",
        )
        layout.addWidget(self._start_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        return page

    def _build_pipeline_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        title = QLabel("Pipeline progress")
        title.setProperty("role", "subtitle")
        layout.addWidget(title)
        self._stage_table = QTableWidget(0, 3)
        self._stage_table.setHorizontalHeaderLabels(["Stage", "Count", "Progress"])
        self._stage_table.verticalHeader().setVisible(False)
        self._stage_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._stage_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._stage_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._stage_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self._stage_table, 1)
        self._stage_rows: dict[str, dict[str, Any]] = {}
        for stage in PIPELINE_STAGES:
            self._add_stage_row(stage)
        actions = QHBoxLayout()
        self._replay_btn = QPushButton("🔁  Replay pending HITL")
        self._replay_btn.clicked.connect(self.replayHltlRequested.emit)
        configure(
            self._replay_btn,
            name="Replay pending HITL",
            description="Re-inject every waiting-for-human chunk to its requesting stage.",
        )
        actions.addWidget(self._replay_btn)
        self._assemble_btn = QPushButton("📦  Assemble now")
        self._assemble_btn.clicked.connect(lambda: self.assembleRequested.emit("epub"))
        self._assemble_btn.setEnabled(False)
        configure(
            self._assemble_btn,
            name="Assemble now",
            description="Trigger the Assembler stage on the current chunks.",
        )
        actions.addWidget(self._assemble_btn)
        actions.addStretch(1)
        layout.addLayout(actions)
        return page

    def _add_stage_row(self, stage: str) -> None:
        row = self._stage_table.rowCount()
        self._stage_table.insertRow(row)
        name_item = QTableWidgetItem(stage.replace("_", " ").title())
        name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self._stage_table.setItem(row, 0, name_item)
        count_item = QTableWidgetItem("0 chunks")
        count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        count_item.setFlags(count_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self._stage_table.setItem(row, 1, count_item)
        from PyQt6.QtWidgets import QProgressBar

        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(0)
        bar.setTextVisible(False)
        self._stage_table.setCellWidget(row, 2, bar)
        self._stage_rows[stage] = {"count": count_item, "progress": bar}

    def _build_review_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        title = QLabel("Review")
        title.setProperty("role", "subtitle")
        layout.addWidget(title)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("STATUS"))
        self._filter = QComboBox()
        self._filter.addItem("All", "")
        for code in (
            "parsed",
            "fast_translated",
            "glossary_applied",
            "consistency_checked",
            "qa_checked",
            "grammar_checked",
            "polished",
            "assembled",
            "waiting_for_human",
            "error",
        ):
            self._filter.addItem(code.replace("_", " ").title(), code)
        self._filter.currentIndexChanged.connect(self._on_filter_changed)
        configure(self._filter, name="Chunk status filter")
        filter_row.addWidget(self._filter, 1)
        layout.addLayout(filter_row)

        self._review_view = QListView()
        self._review_view.setUniformItemSizes(True)
        self._review_view.doubleClicked.connect(self._on_chunk_double_clicked)
        configure(
            self._review_view,
            name="Chunk list",
            description="List of chunks, double-click to inspect.",
        )
        self._review_model = ChunkReviewModel(self._client)
        self._review_model.errorOccurred.connect(
            lambda msg: logger.warning("review model: %s", msg)
        )
        self._review_view.setModel(self._review_model)
        layout.addWidget(self._review_view, 1)
        return page

    # ----- slots -----

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
            "quality": self._quality.currentData() or "balanced",
            "project_dir": self._project_dir or str(Path(self._selected_path).parent),
        }
        self.startRequested.emit(payload)
        self.set_status(
            f"Queued: {Path(self._selected_path).name} "
            f"({payload['source_lang']} → {payload['target_lang']})"
        )
        self.go_to_step(1)

    def _on_filter_changed(self, _idx: int) -> None:
        if self._review_model is None:
            return
        self._review_model.set_filter(self._filter.currentData() or None)
        self._review_model.refresh()

    def _on_chunk_double_clicked(self, index) -> None:  # noqa: ANN001
        chunk = self._review_model.chunk_at(index.row()) if self._review_model else None
        if chunk:
            self.fileSelected.emit(chunk.get("id", ""))

    @staticmethod
    def _status_alias(stage: str) -> str:
        """Map a stage to the chunk status it produces (if any)."""
        return {
            "parser": "parsed",
            "fast_translator": "fast_translated",
            "glossary_applier": "glossary_applied",
            "consistency_checker": "consistency_checked",
            "qa_validator": "qa_checked",
            "grammar_proofer": "grammar_checked",
            "llm_polisher": "polished",
            "assembler": "assembled",
        }.get(stage, stage)


__all__ = ["TranslateTab", "LANGUAGES", "PIPELINE_STAGES"]
