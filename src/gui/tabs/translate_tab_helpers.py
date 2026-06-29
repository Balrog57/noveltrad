"""Helpers for ``TranslateTab``: pure progress math, state labels, page builders.

The translate tab used to be a 1063-line god widget with 39 methods.
After the v4 split the pure logic (no Qt state, no signal wiring) and
the three page builders live here. ``TranslateTab`` keeps the queue
state, the signal wiring, and the methods the test suite pokes at
directly (``_stack``, ``_cloud``, ``_queue_table``, ``_queue_items``,
``_add_queue_item``, ``_on_start``, ``_go_to_select``).

What lives here
---------------
* ``ProgressMath`` -- pure functions that turn chunk counts / stage
  events into a 0-100 progress int and a stage name. No Qt.
* ``StateLabels`` -- pure function that maps a queue state string to
  a human label. Uses ``QObject.tr`` for i18n but takes the ``QObject``
  explicitly, so it has no hidden state.
* ``build_select_page`` -- builds page 0 (drop zone + language /
  quality / format selectors). Returns the page widget; the tab owns
  references to the interactive widgets the builder stashes on it.
* ``build_pipeline_page`` -- builds page 1 (queue table + controls +
  actions). The biggest builder; ~150 lines of pure widget wiring.
* ``build_review_page`` -- builds page 2 (filter + chunk list).

Each builder takes the tab so it can ``tr()`` strings and connect
signals to the tab's slots. The tab keeps the references the builder
sets on it (``self._src``, ``self._tgt``, ``self._cloud``,
``self._queue_table``, ``self._review_model`` ...).
"""
from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListView,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..a11y import configure, set_touch_target
from ..widgets.file_cloud import FileCloud
from .review_model import ChunkReviewModel


# Pipeline stage order. Mirrors ``orchestrator.pipeline.DEFAULT_PIPELINE_ORDER``;
# kept here so the progress math does not have to import the backend.
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

TERMINAL_QUEUE_STATES = {"done", "error"}


# ---------------------------------------------------------------------------
# ProgressMath -- pure functions
# ---------------------------------------------------------------------------


class ProgressMath:
    """Pure helpers that turn chunk counts / stage events into progress.

    No Qt state. The translate tab calls these from
    ``update_pipeline_state`` and ``on_pipeline_event``.
    """

    @staticmethod
    def status_alias(stage: str) -> str:
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

    @staticmethod
    def status_progress_indexes() -> dict[str, int]:
        indexes = {
            ProgressMath.status_alias(stage): i + 1
            for i, stage in enumerate(PIPELINE_STAGES)
        }
        indexes.update(
            {
                "lexicon_ready": PIPELINE_STAGES.index("lexicon_builder") + 1,
                "lexicon_skipped": PIPELINE_STAGES.index("lexicon_builder") + 1,
                "reviewed": PIPELINE_STAGES.index("reviewer") + 1,
            }
        )
        return indexes

    @staticmethod
    def stage_for_status(status: str) -> str:
        for stage in PIPELINE_STAGES:
            if ProgressMath.status_alias(stage) == status:
                return stage
        if status in ("lexicon_ready", "lexicon_skipped"):
            return "lexicon_builder"
        if status == "reviewed":
            return "llm_polisher"
        return status

    @staticmethod
    def progress_from_counts(counts: dict[str, Any], total: int) -> int:
        if total <= 0:
            return 0
        status_to_index = ProgressMath.status_progress_indexes()
        units = 0
        for status, count in counts.items():
            try:
                n = int(count or 0)
            except (TypeError, ValueError):
                n = 0
            units += status_to_index.get(status, 0) * n
        return min(100, int(100 * units / max(1, total * len(PIPELINE_STAGES))))

    @staticmethod
    def stage_from_counts(counts: dict[str, Any]) -> str | None:
        status_to_index = ProgressMath.status_progress_indexes()
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
        return ProgressMath.stage_for_status(best_status)

    @staticmethod
    def progress_from_stage_event(stage: str, percent: Any) -> int:
        try:
            pct = max(0.0, min(100.0, float(percent)))
        except (TypeError, ValueError):
            pct = 0.0
        try:
            idx = PIPELINE_STAGES.index(stage)
        except ValueError:
            idx = 0
        return min(99, int(100 * (idx + pct / 100.0) / len(PIPELINE_STAGES)))


# ---------------------------------------------------------------------------
# StateLabels -- pure label mapper
# ---------------------------------------------------------------------------


class StateLabels:
    """Map a queue state string to a human label, i18n-aware."""

    @staticmethod
    def state_label(tr, state: str) -> str:
        """``tr`` is ``QObject.tr`` (or any callable taking one str)."""
        return {
            "pending": tr("Pending"),
            "queued": tr("Queued"),
            "running": tr("Running"),
            "paused": tr("Paused"),
            "waiting_for_human": tr("Needs review"),
            "done": tr("Done"),
            "error": tr("Error"),
            "stopped": tr("Stopped"),
        }.get(state, state.replace("_", " ").title())


# ---------------------------------------------------------------------------
# Page builders
# ---------------------------------------------------------------------------


def build_select_page(tab, default_target: str) -> QWidget:
    """Page 0: drop zone + language / quality / format selectors.

    Stashes interactive widgets on ``tab`` so the tab can read them
    later (``tab._src``, ``tab._tgt``, ``tab._quality``,
    ``tab._output_format``, ``tab._cloud``, ``tab._start_btn``).
    """
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setSpacing(12)
    layout.setContentsMargins(16, 16, 16, 16)

    lang_row = QHBoxLayout()
    lang_row.addWidget(QLabel(tab.tr("SOURCE LANG")))
    tab._src = QComboBox()
    for code, label in LANGUAGES:
        tab._src.addItem(tab.tr(label), code)
    configure(tab._src, name=tab.tr("Source language"))
    lang_row.addWidget(tab._src, 1)
    lang_row.addSpacing(20)
    lang_row.addWidget(QLabel(tab.tr("TARGET LANG")))
    tab._tgt = QComboBox()
    for code, label in LANGUAGES:
        if code == "auto":
            continue
        tab._tgt.addItem(tab.tr(label), code)
    idx = tab._tgt.findData(default_target)
    if idx >= 0:
        tab._tgt.setCurrentIndex(idx)
    configure(tab._tgt, name=tab.tr("Target language"))
    lang_row.addWidget(tab._tgt, 1)
    layout.addLayout(lang_row)

    quality_row = QHBoxLayout()
    quality_row.addWidget(QLabel(tab.tr("QUALITY")))
    tab._quality = QComboBox()
    tab._quality.addItem(tab.tr("Eco (fast, MT only)"), "eco")
    tab._quality.addItem(tab.tr("Balanced (default)"), "balanced")
    tab._quality.addItem(tab.tr("Premium (full QA + polish)"), "premium")
    configure(tab._quality, name=tab.tr("Quality preset"))
    quality_row.addWidget(tab._quality, 1)
    layout.addLayout(quality_row)

    fmt_row = QHBoxLayout()
    fmt_row.addWidget(QLabel(tab.tr("OUTPUT")))
    tab._output_format = QComboBox()
    tab._output_format.addItem("TXT", "txt")
    tab._output_format.addItem("EPUB", "epub")
    tab._output_format.addItem("EPUB (bilingual)", "epub_bilingual")
    tab._output_format.addItem("DOCX", "docx")
    tab._output_format.addItem("SRT", "srt")
    tab._output_format.setCurrentIndex(0)
    configure(tab._output_format, name=tab.tr("Output format"))
    fmt_row.addWidget(tab._output_format, 1)
    layout.addLayout(fmt_row)

    tab._cloud = FileCloud()
    tab._cloud.filesSelected.connect(tab._on_files)
    layout.addWidget(tab._cloud, 1)

    tab._start_btn = QPushButton(tab.tr("▶  Start Translation"))
    tab._start_btn.setProperty("role", "primary")
    set_touch_target(tab._start_btn, 48)
    tab._start_btn.setEnabled(False)
    tab._start_btn.clicked.connect(tab._on_start)
    configure(
        tab._start_btn,
        name=tab.tr("Start translation"),
        description=tab.tr("Kick off the multi-agent translation pipeline."),
        shortcut="Ctrl+Return",
    )
    layout.addWidget(tab._start_btn, alignment=Qt.AlignmentFlag.AlignCenter)
    return page


def build_pipeline_page(tab) -> QWidget:
    """Page 1: queue table + pipeline controls + actions.

    Stashes the queue table, counter label, active-file label, and the
    pause / resume / stop / clear / new-files / replay / assemble
    buttons on ``tab``.
    """
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(8)
    header_row = QHBoxLayout()
    tab._queue_counter = QLabel(tab.tr("—"))
    tab._queue_counter.setProperty("role", "title")
    tab._queue_counter.setStyleSheet("font-weight: 600; font-size: 16pt;")
    header_row.addWidget(tab._queue_counter)
    tab._queue_active_label = QLabel("")
    tab._queue_active_label.setProperty("role", "muted")
    tab._queue_active_label.setWordWrap(False)
    tab._queue_active_label.setTextInteractionFlags(
        Qt.TextInteractionFlag.TextSelectableByMouse
    )
    header_row.addWidget(tab._queue_active_label, 1)
    layout.addLayout(header_row)

    tab._queue_table = QTableWidget(0, 6)
    tab._queue_table.setHorizontalHeaderLabels(
        [
            tab.tr("File"),
            tab.tr("Status"),
            tab.tr("Stage"),
            tab.tr("Progress"),
            tab.tr("Output / Error"),
            tab.tr("Actions"),
        ]
    )
    tab._queue_table.verticalHeader().setVisible(False)
    hh = tab._queue_table.horizontalHeader()
    hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
    hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
    hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
    hh.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
    hh.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
    tab._queue_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    tab._queue_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
    tab._queue_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    tab._queue_table.verticalHeader().setDefaultSectionSize(28)
    configure(
        tab._queue_table,
        name=tab.tr("File queue"),
        description=tab.tr("Queued files and their translation progress."),
    )
    layout.addWidget(tab._queue_table, 1)

    controls = QHBoxLayout()
    tab._pause_btn = QPushButton(tab.tr("⏸  Pause"))
    tab._pause_btn.setProperty("role", "warning")
    tab._pause_btn.setEnabled(False)
    tab._pause_btn.clicked.connect(tab.pauseRequested.emit)
    configure(
        tab._pause_btn,
        name=tab.tr("Pause translation"),
        description=tab.tr(
            "Pause the current pipeline. Runners finish the chunk they are on and stop."
        ),
        shortcut="Ctrl+Shift+P",
    )
    controls.addWidget(tab._pause_btn)
    tab._resume_btn = QPushButton(tab.tr("▶  Resume"))
    tab._resume_btn.setProperty("role", "primary")
    tab._resume_btn.setEnabled(False)
    tab._resume_btn.clicked.connect(tab.resumeRequested.emit)
    configure(
        tab._resume_btn,
        name=tab.tr("Resume translation"),
        description=tab.tr("Resume the paused pipeline."),
        shortcut="Ctrl+Shift+R",
    )
    controls.addWidget(tab._resume_btn)
    tab._stop_btn = QPushButton(tab.tr("■  Stop"))
    tab._stop_btn.setProperty("role", "danger")
    tab._stop_btn.setEnabled(False)
    tab._stop_btn.clicked.connect(tab.stopRequested.emit)
    configure(
        tab._stop_btn,
        name=tab.tr("Stop translation"),
        description=tab.tr(
            "Stop the pipeline immediately and drop every queued file."
        ),
        shortcut="Ctrl+Shift+S",
    )
    controls.addWidget(tab._stop_btn)
    tab._clear_finished_btn = QPushButton(tab.tr("Clear finished"))
    tab._clear_finished_btn.clicked.connect(tab._on_clear_finished)
    configure(
        tab._clear_finished_btn,
        name=tab.tr("Clear finished files"),
        description=tab.tr(
            "Remove every queue row that already reached a terminal state."
        ),
    )
    controls.addWidget(tab._clear_finished_btn)
    controls.addStretch(1)
    layout.addLayout(controls)

    actions = QHBoxLayout()
    tab._new_files_btn = QPushButton(tab.tr("Retour à la sélection"))
    tab._new_files_btn.clicked.connect(tab._go_to_select)
    configure(
        tab._new_files_btn,
        name=tab.tr("Retour a la selection"),
        description=tab.tr("Go back to step 1 to pick more files."),
    )
    actions.addWidget(tab._new_files_btn)
    tab._replay_btn = QPushButton(tab.tr("Replay HITL questions"))
    tab._replay_btn.setEnabled(False)
    tab._replay_btn.clicked.connect(tab.replayHltlRequested.emit)
    tab._replay_btn.setToolTip(
        tab.tr(
            "Human-In-The-Loop: re-inject every chunk waiting for a human answer (unknown term, ambiguous translation) into the pipeline."
        )
    )
    actions.addWidget(tab._replay_btn)
    tab._assemble_btn = QPushButton(tab.tr("Force assemble now"))
    tab._assemble_btn.clicked.connect(tab._on_assemble_or_open)
    tab._assemble_btn.setEnabled(False)
    tab._assemble_btn.setToolTip(
        tab.tr(
            "Build the output file from the current chunks without waiting for the pipeline to finish. Useful when an LLM chunk is stuck in the polish step."
        )
    )
    actions.addWidget(tab._assemble_btn)
    actions.addStretch(1)
    layout.addLayout(actions)
    return page


def build_review_page(tab) -> QWidget:
    """Page 2: status filter + chunk list (virtualised).

    Stashes ``tab._filter``, ``tab._review_view``,
    ``tab._review_model``, ``tab._review_new_files_btn``.
    """
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(8)
    title = QLabel(tab.tr("Review"))
    title.setProperty("role", "subtitle")
    layout.addWidget(title)

    filter_row = QHBoxLayout()
    filter_row.addWidget(QLabel(tab.tr("STATUS")))
    tab._filter = QComboBox()
    tab._filter.addItem(tab.tr("All"), "")
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
        tab._filter.addItem(code.replace("_", " ").title(), code)
    tab._filter.currentIndexChanged.connect(tab._on_filter_changed)
    configure(tab._filter, name=tab.tr("Chunk status filter"))
    filter_row.addWidget(tab._filter, 1)
    layout.addLayout(filter_row)

    actions = QHBoxLayout()
    tab._review_new_files_btn = QPushButton(tab.tr("Retour à la sélection"))
    tab._review_new_files_btn.clicked.connect(tab._go_to_select)
    configure(
        tab._review_new_files_btn,
        name=tab.tr("Retour a la selection"),
        description=tab.tr("Return to file selection."),
    )
    actions.addWidget(tab._review_new_files_btn)
    actions.addStretch(1)
    layout.addLayout(actions)

    tab._review_view = QListView()
    tab._review_view.setUniformItemSizes(True)
    tab._review_view.doubleClicked.connect(tab._on_chunk_double_clicked)
    configure(
        tab._review_view,
        name=tab.tr("Chunk list"),
        description=tab.tr("List of chunks, double-click to inspect."),
    )
    tab._review_model = ChunkReviewModel(tab._client)
    tab._review_model.errorOccurred.connect(
        lambda msg: __import__("logging").getLogger(__name__).warning(
            "review model: %s", msg
        )
    )
    tab._review_view.setModel(tab._review_model)
    layout.addWidget(tab._review_view, 1)
    return page