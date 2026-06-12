"""Translate tab — 3-step workflow (Select / Pipeline / Review).

Mirrors the TBL UX. Drops one or many files → POST /projects →
orchestrator parses and the activity log shows progress. The tab is
split into three pages, switched by the WebSocket event stream:

  0 Select   — drop zone (FileCloud), source/target language, quality preset.
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
from PyQt6.QtWidgets import (
    QComboBox,
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
from ..widgets.file_cloud import FileCloud
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
        self._selected_paths: list[str] = []
        self._project_dir: str = ""

        # Outer layout = vertical stack: header bar + stacked pages.
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Sticky header.
        self._header = QWidget()
        hlayout = QHBoxLayout(self._header)
        hlayout.setContentsMargins(16, 10, 16, 10)
        self._step_label = QLabel(self.tr("1 · Select"))
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
            labels = [
                self.tr("1 · Select"),
                self.tr("2 · Pipeline"),
                self.tr("3 · Review"),
            ]
            self._step_label.setText(labels[step])

    def update_pipeline_state(self, state: dict[str, Any]) -> None:
        """Refresh the pipeline page from /pipeline/state JSON."""
        ss = state.get("state_store") or {}
        counts = ss.get("chunks_by_status") or {}
        total = ss.get("chunks_total") or 0
        for stage, row in self._stage_rows.items():
            count = counts.get(stage, 0) or counts.get(self._status_alias(stage), 0)
            row["count"].setText(self.tr("{n} chunks").format(n=count))
            row["progress"].setValue(min(100, int(100 * count / max(1, total))))
        polished = counts.get("polished", 0)
        issues = (
            ss.get("qa_issues", 0)
            + ss.get("grammar_issues", 0)
            + ss.get("consistency_flags", 0)
        )
        if total:
            self._progress_label.setText(
                self.tr("{polished}/{total} chunks · {issues} issues").format(
                    polished=polished, total=total, issues=issues
                )
            )
        artifact = state.get("output_artifact") or {}
        if artifact.get("output_path"):
            self._assemble_btn.setEnabled(True)
            self._assemble_btn.setText(self.tr("📦  Open output folder"))
        if any(counts.values()):
            self.go_to_step(1)

    def on_artifact_ready(self, output_path: str) -> None:
        self._assemble_btn.setEnabled(True)
        self._assemble_btn.setText(self.tr("📦  Open output folder"))
        self._progress_label.setText(
            self.tr("Done · {path}").format(path=output_path)
        )
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
        lang_row.addWidget(QLabel(self.tr("SOURCE LANG")))
        self._src = QComboBox()
        for code, label in LANGUAGES:
            self._src.addItem(self.tr(label), code)
        configure(self._src, name=self.tr("Source language"))
        lang_row.addWidget(self._src, 1)
        lang_row.addSpacing(20)
        lang_row.addWidget(QLabel(self.tr("TARGET LANG")))
        self._tgt = QComboBox()
        for code, label in LANGUAGES:
            if code == "auto":
                continue
            self._tgt.addItem(self.tr(label), code)
        idx = self._tgt.findData(default_target)
        if idx >= 0:
            self._tgt.setCurrentIndex(idx)
        configure(self._tgt, name=self.tr("Target language"))
        lang_row.addWidget(self._tgt, 1)
        layout.addLayout(lang_row)

        # Quality preset selector.
        quality_row = QHBoxLayout()
        quality_row.addWidget(QLabel(self.tr("QUALITY")))
        self._quality = QComboBox()
        self._quality.addItem(self.tr("Eco (fast, MT only)"), "eco")
        self._quality.addItem(self.tr("Balanced (default)"), "balanced")
        self._quality.addItem(
            self.tr("Premium (full QA + polish)"), "premium"
        )
        configure(self._quality, name=self.tr("Quality preset"))
        quality_row.addWidget(self._quality, 1)
        layout.addLayout(quality_row)

        # Output format selector.
        fmt_row = QHBoxLayout()
        fmt_row.addWidget(QLabel(self.tr("OUTPUT")))
        self._output_format = QComboBox()
        self._output_format.addItem("TXT", "txt")
        self._output_format.addItem("EPUB", "epub")
        self._output_format.addItem("EPUB (bilingual)", "epub_bilingual")
        self._output_format.addItem("DOCX", "docx")
        self._output_format.addItem("SRT", "srt")
        self._output_format.setCurrentIndex(0)
        configure(self._output_format, name=self.tr("Output format"))
        fmt_row.addWidget(self._output_format, 1)
        layout.addLayout(fmt_row)

        self._cloud = FileCloud()
        self._cloud.filesSelected.connect(self._on_files)
        layout.addWidget(self._cloud, 1)

        self._start_btn = QPushButton(self.tr("▶  Start Translation"))
        self._start_btn.setProperty("role", "primary")
        set_touch_target(self._start_btn, 48)
        self._start_btn.setEnabled(False)
        self._start_btn.clicked.connect(self._on_start)
        configure(
            self._start_btn,
            name=self.tr("Start translation"),
            description=self.tr(
                "Kick off the multi-agent translation pipeline."
            ),
            shortcut="Ctrl+Return",
        )
        layout.addWidget(self._start_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        return page

    def _build_pipeline_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        title = QLabel(self.tr("Pipeline progress"))
        title.setProperty("role", "subtitle")
        layout.addWidget(title)
        self._stage_table = QTableWidget(0, 3)
        self._stage_table.setHorizontalHeaderLabels(
            [self.tr("Stage"), self.tr("Count"), self.tr("Progress")]
        )
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
        self._replay_btn = QPushButton(self.tr("🔁  Replay pending HITL"))
        self._replay_btn.clicked.connect(self.replayHltlRequested.emit)
        configure(
            self._replay_btn,
            name=self.tr("Replay pending HITL"),
            description=self.tr(
                "Re-inject every waiting-for-human chunk to its requesting stage."
            ),
        )
        actions.addWidget(self._replay_btn)
        self._assemble_btn = QPushButton(self.tr("📦  Assemble now"))
        self._assemble_btn.clicked.connect(lambda: self.assembleRequested.emit("epub"))
        self._assemble_btn.setEnabled(False)
        configure(
            self._assemble_btn,
            name=self.tr("Assemble now"),
            description=self.tr("Trigger the Assembler stage on the current chunks."),
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
        count_item = QTableWidgetItem(self.tr("0 chunks"))
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
        title = QLabel(self.tr("Review"))
        title.setProperty("role", "subtitle")
        layout.addWidget(title)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel(self.tr("STATUS")))
        self._filter = QComboBox()
        self._filter.addItem(self.tr("All"), "")
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
        configure(self._filter, name=self.tr("Chunk status filter"))
        filter_row.addWidget(self._filter, 1)
        layout.addLayout(filter_row)

        self._review_view = QListView()
        self._review_view.setUniformItemSizes(True)
        self._review_view.doubleClicked.connect(self._on_chunk_double_clicked)
        configure(
            self._review_view,
            name=self.tr("Chunk list"),
            description=self.tr("List of chunks, double-click to inspect."),
        )
        self._review_model = ChunkReviewModel(self._client)
        self._review_model.errorOccurred.connect(
            lambda msg: logger.warning("review model: %s", msg)
        )
        self._review_view.setModel(self._review_model)
        layout.addWidget(self._review_view, 1)
        return page

    # ----- slots -----

    def _on_files(self, paths: list[str]) -> None:
        self._selected_paths = list(paths)
        self._start_btn.setEnabled(bool(paths))
        if paths:
            self.fileSelected.emit(paths[0])

    def _on_start(self) -> None:
        if not self._selected_paths:
            return
        source_lang = self._src.currentData() or "auto"
        target_lang = self._tgt.currentData() or "fr"
        quality = self._quality.currentData() or "balanced"
        output_format = self._output_format.currentData() or "txt"
        project_dir = self._project_dir or str(
            Path(self._selected_paths[0]).parent
        )
        # Emit one start per file so the orchestrator queues them
        # sequentially and tags each chunk's source_file accordingly.
        # For the v1 batch UI we keep the startRequested signal
        # single-payload: callers iterate the cloud's selection.
        for path in self._selected_paths:
            payload = {
                "source_path": path,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "quality": quality,
                "output_format": output_format,
                "project_dir": project_dir,
            }
            self.startRequested.emit(payload)
        names = ", ".join(Path(p).name for p in self._selected_paths)
        self.set_status(
            self.tr("Queued: {names} ({src} → {tgt})").format(
                names=names, src=source_lang, tgt=target_lang
            )
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
