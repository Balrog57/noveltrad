"""Translate tab — 3-step workflow (Select / Pipeline / Review).

Mirrors the TBL UX. Drops one or many files → POST /projects →
orchestrator parses and the activity log shows progress. The tab is
split into three pages, switched by the WebSocket event stream:

  0 Select   — drop zone (FileCloud), source/target language, quality preset.
  1 Pipeline — per-stage status cards, pause/resume/stop controls,
               "Re-run + Replay pending questions actions.
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
    QProgressBar,
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
    "terminology_researcher",
    "glossary_applier",
    "consistency_checker",
    "qa_validator",
    "grammar_proofer",
    "reviewer",
    "llm_polisher",
    "assembler",
)

TERMINAL_QUEUE_STATES = {"done", "error"}


class TranslateTab(QWidget):
    startRequested = pyqtSignal(dict)
    fileSelected = pyqtSignal(str)
    replayHltlRequested = pyqtSignal()
    retryRequested = pyqtSignal(str)  # path of errored project
    assembleRequested = pyqtSignal(str)  # format
    pauseRequested = pyqtSignal()
    resumeRequested = pyqtSignal()
    stopRequested = pyqtSignal()
    fileRemoved = pyqtSignal(str)  # path
    queueCompleted = pyqtSignal(dict)  # {done, failed, total}

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
        self._user_requested_select = False
        self._queue_items: list[dict[str, Any]] = []
        self._queue_by_path: dict[str, dict[str, Any]] = {}
        self._queue_by_project_id: dict[str, dict[str, Any]] = {}
        self._active_project_id: str | None = None

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
        self._update_pipeline_controls(state)
        self._update_queue_counter()
        project = state.get("project") or {}
        if project:
            self._sync_active_project(project)
        self._sync_queued_projects(state.get("project_queue") or [])

        ss = state.get("state_store") or {}
        counts = ss.get("chunks_by_status") or {}
        total = ss.get("chunks_total") or 0
        active = self._active_queue_item()
        if active is not None:
            active["progress"] = max(
                int(active.get("progress", 0)),
                self._progress_from_counts(counts, total),
            )
            active["state"] = project.get("status") or active.get("state", "running")
            active["current_stage"] = self._stage_from_counts(counts) or active.get(
                "current_stage", "parser"
            )
            self._refresh_queue_row(active)
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
            self._assemble_btn.setText(self.tr("Open output folder"))
        if any(counts.values()) and not self._user_requested_select:
            self.go_to_step(1)

    def on_artifact_ready(self, output_path: str) -> None:
        self._assemble_btn.setEnabled(True)
        self._assemble_btn.setText(self.tr("Open output folder"))
        active = self._active_queue_item()
        if active is not None:
            active["state"] = "done"
            active["current_stage"] = "assembler"
            active["progress"] = 100
            active["output_path"] = output_path
            self._refresh_queue_row(active)
        self._progress_label.setText(
            self.tr("Done · {path}").format(path=output_path)
        )
        # Refresh review list and switch to it.
        if self._review_model is not None:
            self._review_model.refresh()
        self.go_to_step(1 if self._queue_items else 2)
        self._maybe_emit_queue_completed()

    def on_project_created(
        self, payload: dict[str, Any], response: dict[str, Any]
    ) -> None:
        """Attach POST /projects metadata to the pre-created queue row."""
        path = str(
            (payload.get("source_paths") or [payload.get("source_path") or ""])[0]
        )
        item = self._queue_by_path.get(path)
        if item is None:
            item = self._add_queue_item(path)
        pid = response.get("project_id") or ""
        if pid:
            item["project_id"] = pid
            self._queue_by_project_id[pid] = item
        item["state"] = "queued" if response.get("queue_position", 0) else "running"
        item["current_stage"] = "waiting" if item["state"] == "queued" else "parser"
        if item["state"] == "running":
            self._active_project_id = pid or item.get("project_id")
        self._refresh_queue_row(item)

    def on_project_start_failed(self, payload: dict[str, Any], error: str) -> None:
        path = str(
            (payload.get("source_paths") or [payload.get("source_path") or ""])[0]
        )
        item = self._queue_by_path.get(path)
        if item is None:
            item = self._add_queue_item(path)
        item["state"] = "error"
        item["current_stage"] = "start"
        item["error"] = error
        self._refresh_queue_row(item)

    def on_pipeline_event(self, event: dict[str, Any]) -> None:
        """Apply live backend events to the file queue table."""
        kind = event.get("type")
        pid = event.get("project_id") or self._active_project_id
        item = self._queue_by_project_id.get(pid or "") if pid else None
        if item is None:
            item = self._active_queue_item()

        if kind == "project_queued":
            item = self._queue_by_project_id.get(event.get("project_id", ""))
            if item is not None:
                item["state"] = "queued"
                item["current_stage"] = "waiting"
                self._refresh_queue_row(item)
            return

        if kind in ("pipeline_started", "project_started_from_queue"):
            pid = event.get("project_id")
            item = self._queue_by_project_id.get(pid or "") if pid else item
            if item is not None:
                self._active_project_id = item.get("project_id") or pid
                item["state"] = "running"
                item["current_stage"] = "parser"
                self._refresh_queue_row(item)
                self.go_to_step(1)
            return

        if item is None:
            return

        if kind in ("agent_progress", "stage_progress", "chunk_progress"):
            stage = event.get("stage") or item.get("current_stage") or "parser"
            item["state"] = "running"
            item["current_stage"] = stage
            item["progress"] = max(
                int(item.get("progress", 0)),
                self._progress_from_stage_event(stage, event.get("percent")),
            )
        elif kind == "agent_done":
            stage = event.get("stage") or item.get("current_stage") or "pipeline"
            item["current_stage"] = stage
            item["progress"] = max(
                int(item.get("progress", 0)),
                self._progress_from_stage_event(stage, 100),
            )
        elif kind == "hltl_alert":
            item["state"] = "waiting_for_human"
            item["current_stage"] = event.get("stage") or item.get("current_stage")
        elif kind == "agent_error":
            item["state"] = "error"
            item["current_stage"] = event.get("stage") or item.get("current_stage")
            payload = event.get("payload") or {}
            item["error"] = payload.get("message") or payload.get("error_kind") or ""
        elif kind == "assemble_triggered":
            item["state"] = "running"
            item["current_stage"] = "assembler"
            item["progress"] = max(int(item.get("progress", 0)), 95)
        elif kind == "artifact_ready":
            item["state"] = "done"
            item["current_stage"] = "assembler"
            item["progress"] = 100
            item["output_path"] = event.get("output_path") or ""
        elif kind == "project_queue_failed":
            item["state"] = "error"
            item["current_stage"] = "queue"
            item["error"] = self.tr("Could not start queued project.")
        else:
            return
        self._refresh_queue_row(item)
        self._maybe_emit_queue_completed()

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
        # Compact header: "X / Y" (done / total) and current file
        # name. We deliberately do NOT show the long list of every
        # file here because with 2000+ queued items it would push
        # the actual progress bars off the screen.
        header_row = QHBoxLayout()
        self._queue_counter = QLabel(self.tr("—"))
        self._queue_counter.setProperty("role", "title")
        self._queue_counter.setStyleSheet("font-weight: 600; font-size: 16pt;")
        header_row.addWidget(self._queue_counter)
        self._queue_active_label = QLabel("")
        self._queue_active_label.setProperty("role", "muted")
        self._queue_active_label.setWordWrap(False)
        self._queue_active_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        header_row.addWidget(self._queue_active_label, 1)
        layout.addLayout(header_row)
        # Per-file queue. One row per file with progress bar,
        # percentage label, current stage, and a remove button
        # on the right. Scrolling stays smooth even with 2000+ rows
        # because we set UniformItemSizes + no selection + no focus.
        self._queue_table = QTableWidget(0, 6)
        self._queue_table.setHorizontalHeaderLabels(
            [
                self.tr("File"),
                self.tr("Status"),
                self.tr("Stage"),
                self.tr("Progress"),
                self.tr("Output / Error"),
                self.tr("Actions"),
            ]
        )
        self._queue_table.verticalHeader().setVisible(False)
        # File column stretches, the rest is fixed-width so a
        # 2000-row table does not allocate widgets for columns
        # the user never reads.
        from PyQt6.QtWidgets import QHeaderView as _HV
        hh = self._queue_table.horizontalHeader()
        hh.setSectionResizeMode(0, _HV.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, _HV.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, _HV.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, _HV.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(4, _HV.ResizeMode.Stretch)
        hh.setSectionResizeMode(5, _HV.ResizeMode.ResizeToContents)
        self._queue_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._queue_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._queue_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._queue_table.verticalHeader().setDefaultSectionSize(28)
        configure(
            self._queue_table,
            name=self.tr("File queue"),
            description=self.tr("Queued files and their translation progress."),
        )
        layout.addWidget(self._queue_table, 1)

        # Pipeline control row: pause / resume / stop the running
        # pipeline. These affect the whole backend, not a single file.
        controls = QHBoxLayout()
        self._pause_btn = QPushButton(self.tr("⏸  Pause"))
        self._pause_btn.setProperty("role", "warning")
        self._pause_btn.setEnabled(False)
        self._pause_btn.clicked.connect(self.pauseRequested.emit)
        configure(
            self._pause_btn,
            name=self.tr("Pause translation"),
            description=self.tr(
                "Pause the current pipeline. Runners finish the chunk "
                "they are on and stop."
            ),
            shortcut="Ctrl+Shift+P",
        )
        controls.addWidget(self._pause_btn)
        self._resume_btn = QPushButton(self.tr("▶  Resume"))
        self._resume_btn.setProperty("role", "primary")
        self._resume_btn.setEnabled(False)
        self._resume_btn.clicked.connect(self.resumeRequested.emit)
        configure(
            self._resume_btn,
            name=self.tr("Resume translation"),
            description=self.tr("Resume the paused pipeline."),
            shortcut="Ctrl+Shift+R",
        )
        controls.addWidget(self._resume_btn)
        self._stop_btn = QPushButton(self.tr("■  Stop"))
        self._stop_btn.setProperty("role", "danger")
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self.stopRequested.emit)
        configure(
            self._stop_btn,
            name=self.tr("Stop translation"),
            description=self.tr(
                "Stop the pipeline immediately and drop every queued file."
            ),
            shortcut="Ctrl+Shift+S",
        )
        controls.addWidget(self._stop_btn)
        self._clear_finished_btn = QPushButton(self.tr("Clear finished"))
        self._clear_finished_btn.clicked.connect(self._on_clear_finished)
        configure(
            self._clear_finished_btn,
            name=self.tr("Clear finished files"),
            description=self.tr(
                "Remove every queue row that already reached a terminal state."
            ),
        )
        controls.addWidget(self._clear_finished_btn)
        controls.addStretch(1)
        layout.addLayout(controls)
        actions = QHBoxLayout()
        self._new_files_btn = QPushButton(self.tr("Retour à la sélection"))
        self._new_files_btn.clicked.connect(self._go_to_select)
        configure(
            self._new_files_btn,
            name=self.tr("Retour a la selection"),
            description=self.tr("Go back to step 1 to pick more files."),
        )
        actions.addWidget(self._new_files_btn)
        # HITL = Human-In-The-Loop. The button stays disabled until
        # the backend reports chunks waiting for a human answer
        # (for example an unknown term). The tooltip explains it.
        self._replay_btn = QPushButton(self.tr("Replay HITL questions"))
        self._replay_btn.setEnabled(False)
        self._replay_btn.clicked.connect(self.replayHltlRequested.emit)
        self._replay_btn.setToolTip(
            self.tr("Human-In-The-Loop: re-inject every chunk waiting for a human answer (unknown term, ambiguous translation) into the pipeline.")
        )
        actions.addWidget(self._replay_btn)
        # Force the Assembler stage to run right now (instead of
        # waiting for the auto-assemble when the penultimate
 # stage reaches 100%). Useful when an LLM chunk is stuck.
        self._assemble_btn = QPushButton(self.tr("Force assemble now"))
        self._assemble_btn.clicked.connect(lambda: self.assembleRequested.emit(self._output_format.currentData() or "epub"))
        self._assemble_btn.setEnabled(False)
        self._assemble_btn.setToolTip(
            self.tr("Build the output file from the current chunks without waiting for the pipeline to finish. Useful when an LLM chunk is stuck in the polish step.")
        )
        actions.addWidget(self._assemble_btn)
        actions.addStretch(1)
        layout.addLayout(actions)
        return page


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

        actions = QHBoxLayout()
        self._review_new_files_btn = QPushButton(self.tr("Retour à la sélection"))
        self._review_new_files_btn.clicked.connect(self._go_to_select)
        configure(
            self._review_new_files_btn,
            name=self.tr("Retour a la selection"),
            description=self.tr("Return to file selection."),
        )
        actions.addWidget(self._review_new_files_btn)
        actions.addStretch(1)
        layout.addLayout(actions)

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
        self._user_requested_select = False
        source_lang = self._src.currentData() or "auto"
        target_lang = self._tgt.currentData() or "fr"
        quality = self._quality.currentData() or "balanced"
        output_format = self._output_format.currentData() or "txt"
        project_dir = self._project_dir or str(
            Path(self._selected_paths[0]).parent
        )
        # Emit one start per file so the backend creates one project
        # per file and queues them ``a la file``. The orchestrator
        # auto-starts the next queued project once the current one
        # finishes (assembler done). The response also reports a
        # ``queue_position`` so the GUI can show the user where each
        # file sits in the queue.
        n = len(self._selected_paths)
        self._reset_queue()
        for path in self._selected_paths:
            self._add_queue_item(path)
        for i, path in enumerate(self._selected_paths):
            payload = {
                "source_path": path,
                "source_paths": [path],
                "source_lang": source_lang,
                "target_lang": target_lang,
                "quality": quality,
                "output_format": output_format,
                "project_dir": project_dir,
                "_queue_index": i + 1,
                "_queue_total": n,
            }
            self.startRequested.emit(payload)
        # Short status in the header. The full file list lives in
        # the per-file queue table on the Pipeline page, so the
        # header just shows a counter (X / Y) and the active file.
        n = len(self._selected_paths)
        self.set_status(
            self.tr("Queued {n} file(s)").format(n=n)
        )
        self.go_to_step(1)

    def _go_to_select(self) -> None:
        self._user_requested_select = True
        self.go_to_step(0)
        self.set_status(self.tr("Select files to translate."))

    def _on_filter_changed(self, _idx: int) -> None:
        if self._review_model is None:
            return
        self._review_model.set_filter(self._filter.currentData() or None)
        self._review_model.refresh()

    def _on_chunk_double_clicked(self, index) -> None:  # noqa: ANN001
        chunk = self._review_model.chunk_at(index.row()) if self._review_model else None
        if chunk:
            self.fileSelected.emit(chunk.get("id", ""))

    def _reset_queue(self) -> None:
        self._queue_items.clear()
        self._queue_by_path.clear()
        self._queue_by_project_id.clear()
        self._active_project_id = None
        self._queue_table.setRowCount(0)
        self._queue_counter.setText(self.tr("—"))
        self._queue_active_label.setText("")
        if getattr(self, "_pause_btn", None):
            self._pause_btn.setEnabled(False)
        self._resume_btn.setEnabled(False)
        self._stop_btn.setEnabled(False)

    def _add_queue_item(self, path: str) -> dict[str, Any]:
        if path in self._queue_by_path:
            return self._queue_by_path[path]
        row = self._queue_table.rowCount()
        self._queue_table.insertRow(row)
        name_item = QTableWidgetItem(Path(path).name)
        name_item.setToolTip(path)
        status_item = QTableWidgetItem(self.tr("Pending"))
        stage_item = QTableWidgetItem(self.tr("Waiting"))
        detail_item = QTableWidgetItem("")
        for table_item in (name_item, status_item, stage_item, detail_item):
            table_item.setFlags(table_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(0)
        bar.setFormat("%p%")
        self._queue_table.setItem(row, 0, name_item)
        self._queue_table.setItem(row, 1, status_item)
        self._queue_table.setItem(row, 2, stage_item)
        self._queue_table.setCellWidget(row, 3, bar)
        self._queue_table.setItem(row, 4, detail_item)
        # Per-row remove button (column 5). Always enabled so the user
        # can drop a queued file; we ask the backend to remove it and
        # the backend will 409 on the currently-running project.
        # Action buttons container (column 5). We always need the remove
        # button; a "Retry" button is shown/hidden in _refresh_queue_row
        # when the item enters / leaves the error state.
        actions_widget = QWidget()
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(4)

        remove_btn = QPushButton(self.tr("✕"))
        remove_btn.setFixedSize(32, 28)
        remove_btn.setStyleSheet("font-size: 14pt; font-weight: 600;")
        remove_btn.setToolTip(self.tr("Remove this file from the queue"))
        remove_btn.clicked.connect(
            lambda _checked=False, p=path: self._on_remove_file(p)
        )
        actions_layout.addWidget(remove_btn)

        retry_btn = QPushButton(self.tr("Retry"))
        retry_btn.setProperty("role", "primary")
        retry_btn.setFixedHeight(28)
        retry_btn.setToolTip(
            self.tr("Re-submit errored chunks to the pipeline")
        )
        retry_btn.clicked.connect(
            lambda _checked=False, p=path: self.retryRequested.emit(p)
        )
        retry_btn.hide()
        actions_layout.addWidget(retry_btn)

        self._queue_table.setCellWidget(row, 5, actions_widget)
        item: dict[str, Any] = {
            "row": row,
            "project_id": "",
            "path": path,
            "name": Path(path).name,
            "state": "pending",
            "current_stage": "waiting",
            "progress": 0,
            "output_path": "",
            "error": "",
            "_status_item": status_item,
            "_stage_item": stage_item,
            "_detail_item": detail_item,
            "_progress_bar": bar,
            "_remove_btn": remove_btn,
            "_retry_btn": retry_btn,
        }
        self._queue_items.append(item)
        self._queue_by_path[path] = item
        return item

    def _on_remove_file(self, path: str) -> None:
        item = self._queue_by_path.get(path)
        if item is None:
            return
        if item.get("state") == "running":
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.information(
                self,
                self.tr("Cannot remove"),
                self.tr(
                    "{name} is the running project. Stop the pipeline "
                    "or wait for it to finish before removing it."
                ).format(name=item.get("name") or path),
            )
            return
        if item.get("state") in TERMINAL_QUEUE_STATES:
            # Already done or errored — just drop the local row.
            self._drop_row(item)
            return
        # Otherwise (pending or queued) ask the backend to drop the
        # project, then remove the row locally.
        pid = item.get("project_id") or ""
        if pid:
            self.fileRemoved.emit(path)
        self._drop_row(item)

    def _drop_row(self, item: dict[str, Any]) -> None:
        path = item.get("path") or ""
        if not path:
            return
        row = item.get("row", -1)
        if row >= 0 and row < self._queue_table.rowCount():
            self._queue_table.removeCellWidget(row, 5)
            self._queue_table.removeRow(row)
        self._queue_items.remove(item)
        self._queue_by_path.pop(path, None)
        pid = item.get("project_id") or ""
        if pid:
            self._queue_by_project_id.pop(pid, None)
        # Re-index subsequent rows so the underlying dicts stay sane.
        for i, it in enumerate(self._queue_items):
            if it["row"] > row:
                it["row"] -= 1
        self._maybe_emit_queue_completed()

    def _on_clear_finished(self) -> None:
        for item in list(self._queue_items):
            if item.get("state") in TERMINAL_QUEUE_STATES:
                self._drop_row(item)

    def _update_queue_counter(self) -> None:
        """Update the compact header counter (X / Y).

        Done / error / stopped all count as finished. Pending /
        queued / running / paused / waiting_for_human all count
        as in progress. When everything is finished, we show N / N.
        """
        total = len(self._queue_items)
        finished = sum(
            1 for it in self._queue_items
            if it.get("state") in TERMINAL_QUEUE_STATES
        )
        if getattr(self, "_queue_counter", None):
            if total == 0:
                self._queue_counter.setText(
                    self.tr("—  (aucun fichier)")
                )
            elif finished == 0:
                # Nothing finished yet — show just the count once,
                # no "0/" prefix which would be redundant with the
                # step header.
                self._queue_counter.setText(
                    self.tr("→ {total}").format(total=total)
                )
            elif finished < total:
                self._queue_counter.setText(
                    self.tr("{done} / {total}").format(done=finished, total=total)
                )
            else:
                self._queue_counter.setText(
                    self.tr("{done} / {total}  ✓").format(done=finished, total=total)
                )
        if getattr(self, "_queue_active_label", None):
            active = self._active_queue_item()
            if active is not None:
                name = active.get("name") or active.get("path") or ""
                self._queue_active_label.setText(
                    self.tr("Active: {name}").format(name=name)
                )
            else:
                self._queue_active_label.setText("")

    def _update_pipeline_controls(self, state: dict[str, Any]) -> None:
        """Toggle Pause / Resume / Stop from the orchestrator state.

        ``running`` -> Pause and Stop enabled, Resume disabled.
        ``paused``  -> Resume and Stop enabled, Pause disabled.
        otherwise   -> all three disabled.
        """
        if not getattr(self, "_pause_btn", None):
            return
        proj = state.get("project") or {}
        status = proj.get("status") if proj else None
        self._pause_btn.setEnabled(status == "running")
        self._resume_btn.setEnabled(status == "paused")
        self._stop_btn.setEnabled(status in ("running", "paused"))

    def _maybe_emit_queue_completed(self) -> None:
        """Emit ``queueCompleted`` when every queue row is terminal.

        A row reaches a terminal state (``done`` / ``error`` /
        ``stopped``) when the assembler has written the output for
        that project, or when the project failed. Once all rows
        are terminal, the main window pops a success / failure
        notification with a sound.
        """
        if not self._queue_items:
            return
        pending = [
            it for it in self._queue_items
            if it.get("state") not in TERMINAL_QUEUE_STATES
        ]
        if pending:
            return
        done = sum(1 for it in self._queue_items if it.get("state") == "done")
        failed = sum(
            1 for it in self._queue_items
            if it.get("state") in ("error", "stopped")
        )
        self.queueCompleted.emit(
            {"done": done, "failed": failed, "total": len(self._queue_items)}
        )

    def _refresh_queue_row(self, item: dict[str, Any]) -> None:
        item["_status_item"].setText(self._state_label(item.get("state", "")))
        stage = str(item.get("current_stage") or "waiting")
        item["_stage_item"].setText(stage.replace("_", " ").title())
        item["_progress_bar"].setValue(max(0, min(100, int(item.get("progress", 0)))))
        detail = item.get("error") or item.get("output_path") or item.get("project_id") or ""
        item["_detail_item"].setText(str(detail))
        item["_detail_item"].setToolTip(str(detail))
        # Show Retry button when in error state, hide otherwise.
        retry_btn = item.get("_retry_btn")
        if retry_btn:
            retry_btn.setVisible(item.get("state") == "error")

    def _sync_active_project(self, project: dict[str, Any]) -> None:
        pid = project.get("project_id") or ""
        paths = project.get("source_paths") or []
        path = str(project.get("source_path") or (paths[0] if paths else ""))
        if not path:
            return
        item = self._queue_by_project_id.get(pid) or self._queue_by_path.get(path)
        if item is None:
            item = self._add_queue_item(path)
        if pid:
            item["project_id"] = pid
            self._queue_by_project_id[pid] = item
            self._active_project_id = pid
        if item.get("state") not in TERMINAL_QUEUE_STATES:
            item["state"] = project.get("status") or "running"
        self._refresh_queue_row(item)

    def _sync_queued_projects(self, entries: list[dict[str, Any]]) -> None:
        for entry in entries:
            pid = entry.get("project_id") or ""
            paths = entry.get("source_paths") or []
            path = str(entry.get("source_path") or (paths[0] if paths else ""))
            if not path:
                continue
            item = self._queue_by_project_id.get(pid) or self._queue_by_path.get(path)
            if item is None:
                item = self._add_queue_item(path)
            if pid:
                item["project_id"] = pid
                self._queue_by_project_id[pid] = item
            if item.get("state") not in TERMINAL_QUEUE_STATES:
                item["state"] = "queued"
                item["current_stage"] = "waiting"
            self._refresh_queue_row(item)

    def _active_queue_item(self) -> dict[str, Any] | None:
        if self._active_project_id:
            item = self._queue_by_project_id.get(self._active_project_id)
            if item is not None:
                return item
        for item in self._queue_items:
            if item.get("state") in ("running", "paused", "waiting_for_human"):
                return item
        return None

    def _progress_from_counts(self, counts: dict[str, Any], total: int) -> int:
        if total <= 0:
            return 0
        status_to_index = self._status_progress_indexes()
        units = 0
        for status, count in counts.items():
            try:
                n = int(count or 0)
            except (TypeError, ValueError):
                n = 0
            units += status_to_index.get(status, 0) * n
        return min(100, int(100 * units / max(1, total * len(PIPELINE_STAGES))))

    def _stage_from_counts(self, counts: dict[str, Any]) -> str | None:
        status_to_index = self._status_progress_indexes()
        best_status = ""
        best_index = -1
        for status, count in counts.items():
            if not count:
                continue
            idx = status_to_index.get(status, -1)
            if idx > best_index:
                best_status = status
                best_index = idx
        if not best_status:
            return None
        return self._stage_for_status(best_status)

    def _progress_from_stage_event(self, stage: str, percent: Any) -> int:
        try:
            pct = max(0.0, min(100.0, float(percent)))
        except (TypeError, ValueError):
            pct = 0.0
        try:
            idx = PIPELINE_STAGES.index(stage)
        except ValueError:
            idx = 0
        return min(99, int(100 * (idx + pct / 100.0) / len(PIPELINE_STAGES)))

    @classmethod
    def _status_progress_indexes(cls) -> dict[str, int]:
        indexes = {
            cls._status_alias(stage): i + 1 for i, stage in enumerate(PIPELINE_STAGES)
        }
        indexes.update(
            {
                "lexicon_ready": PIPELINE_STAGES.index("lexicon_builder") + 1,
                "lexicon_skipped": PIPELINE_STAGES.index("lexicon_builder") + 1,
                "reviewed": PIPELINE_STAGES.index("reviewer") + 1,
            }
        )
        return indexes

    @classmethod
    def _stage_for_status(cls, status: str) -> str:
        for stage in PIPELINE_STAGES:
            if cls._status_alias(stage) == status:
                return stage
        if status in ("lexicon_ready", "lexicon_skipped"):
            return "lexicon_builder"
        if status == "reviewed":
            return "llm_polisher"
        return status

    def _state_label(self, state: str) -> str:
        return {
            "pending": self.tr("Pending"),
            "queued": self.tr("Queued"),
            "running": self.tr("Running"),
            "paused": self.tr("Paused"),
            "waiting_for_human": self.tr("Needs review"),
            "done": self.tr("Done"),
            "error": self.tr("Error"),
            "stopped": self.tr("Stopped"),
        }.get(state, state.replace("_", " ").title())

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
