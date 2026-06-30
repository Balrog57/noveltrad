"""Translate tab — 3-step workflow (Select / Pipeline / Review).

Mirrors the TBL UX. Drops one or many files → POST /projects →
orchestrator parses and the activity log shows progress. The tab is
split into three pages, switched by the WebSocket event stream:

  0 Select   — drop zone (FileCloud), source/target language, quality preset.
  1 Pipeline — per-stage status cards, pause/resume/stop controls,
               "Re-run + Replay pending questions actions.
  2 Review   — virtualised list of chunks with status filter, double
               click opens the chunk detail dialog.

Module layout
-------------
After the v4 split the pure progress math, the state-label mapper, and
the three page builders live in :mod:`.translate_tab_helpers`. This
module holds the queue state, the signal wiring, and the methods the
test suite pokes at directly (``_stack``, ``_cloud``, ``_queue_table``,
``_queue_items``, ``_add_queue_item``, ``_on_start``,
``_go_to_select``). The pure helpers are thin delegates so the
private API stays stable.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ..a11y import configure

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QProgressBar,
    QPushButton,
    QStackedLayout,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .translate_tab_helpers import (
    LANGUAGES,
    PIPELINE_STAGES,
    TERMINAL_QUEUE_STATES,
    ProgressMath,
    StateLabels,
    build_pipeline_page,
    build_review_page,
    build_select_page,
)

logger = logging.getLogger(__name__)

# Re-export the constants the test suite / main window may import.
__all__ = ["TranslateTab", "LANGUAGES", "PIPELINE_STAGES", "TERMINAL_QUEUE_STATES"]


class TranslateTab(QWidget):
    startRequested = pyqtSignal(dict)
    fileSelected = pyqtSignal(str)
    replayHltlRequested = pyqtSignal()
    retryRequested = pyqtSignal(str)  # path of errored project
    assembleRequested = pyqtSignal(str)  # format
    outputFolderRequested = pyqtSignal(str)  # output_path to open
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
        self._output_artifact_path: str = ""

        # Outer layout = vertical stack: header bar + stacked pages.
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Sticky header.
        self._header = QWidget()
        hlayout = QVBoxLayout(self._header)
        hlayout.setContentsMargins(16, 10, 16, 10)
        self._step_label = QLabel(self.tr("1 · Select"))
        self._step_label.setProperty("role", "title")
        hlayout.addWidget(self._step_label)
        self._progress_label = QLabel("")
        self._progress_label.setProperty("role", "muted")
        hlayout.addWidget(self._progress_label)
        outer.addWidget(self._header)

        self._stack = QStackedLayout()
        outer.addLayout(self._stack, 1)

        # Page 0: Select.
        self._select_page = build_select_page(self, default_target)
        self._stack.addWidget(self._select_page)

        # Page 1: Pipeline.
        self._pipeline_page = build_pipeline_page(self)
        self._stack.addWidget(self._pipeline_page)

        # Page 2: Review.
        self._review_page = build_review_page(self)
        self._stack.addWidget(self._review_page)

    # ----- public API -----

    def set_client(self, client: Any) -> None:
        self._client = client
        if self._review_model is not None:
            self._review_model._client = client  # type: ignore[attr-defined]

    def set_project(self, proj: dict[str, Any]) -> None:
        """Set the active project context for this tab."""
        self._project = proj
        self._project_dir = proj.get("project_dir", "")
        # Update header to show project name.
        name = proj.get("name", proj.get("project_id", "?")[:8])
        self._step_label.setText(self.tr("🔵 {name} — Pipeline").format(name=name))

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
                ProgressMath.progress_from_counts(counts, total),
            )
            active["state"] = project.get("status") or active.get("state", "running")
            active["current_stage"] = (
                ProgressMath.stage_from_counts(counts)
                or active.get("current_stage", "parser")
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
            self._output_artifact_path = artifact["output_path"]
            self._assemble_btn.setEnabled(True)
            self._assemble_btn.setText(self.tr("Open output folder"))
            self._assemble_btn.setToolTip(
                self.tr("Open the folder containing the translated file.")
            )
        if any(counts.values()) and not self._user_requested_select:
            self.go_to_step(1)

    def on_artifact_ready(self, output_path: str) -> None:
        self._output_artifact_path = output_path
        self._assemble_btn.setEnabled(True)
        self._assemble_btn.setText(self.tr("Open output folder"))
        self._assemble_btn.setToolTip(
            self.tr("Open the folder containing the translated file.")
        )
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
                ProgressMath.progress_from_stage_event(stage, event.get("percent")),
            )
        elif kind == "agent_done":
            stage = event.get("stage") or item.get("current_stage") or "pipeline"
            item["current_stage"] = stage
            item["progress"] = max(
                int(item.get("progress", 0)),
                ProgressMath.progress_from_stage_event(stage, 100),
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
        self.set_status(self.tr("Queued {n} file(s)").format(n=n))
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

    def _on_assemble_or_open(self) -> None:
        """Dispatch: open folder if artifact exists, otherwise force assemble."""
        if self._output_artifact_path:
            self.outputFolderRequested.emit(self._output_artifact_path)
        else:
            self.assembleRequested.emit(self._output_format.currentData() or "epub")

    # ----- queue management -----

    def _reset_queue(self) -> None:
        self._queue_items.clear()
        self._queue_by_path.clear()
        self._queue_by_project_id.clear()
        self._active_project_id = None
        self._output_artifact_path = ""
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
        actions_widget = QWidget()
        actions_layout = QVBoxLayout(actions_widget)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(4)

        remove_btn = QPushButton(self.tr("✕"))
        remove_btn.setFixedSize(32, 28)
        remove_btn.setStyleSheet("font-size: 14pt; font-weight: 600;")
        remove_btn.setToolTip(self.tr("Remove this file from the queue"))
        remove_btn.clicked.connect(
            lambda _checked=False, p=path: self._on_remove_file(p)
        )
        file_name = Path(path).name
        configure(remove_btn, name=self.tr("Remove {file}").format(file=file_name))
        actions_layout.addWidget(remove_btn)

        retry_btn = QPushButton(self.tr("Retry"))
        retry_btn.setProperty("role", "primary")
        retry_btn.setFixedHeight(28)
        retry_btn.setToolTip(self.tr("Re-submit errored chunks to the pipeline"))
        retry_btn.clicked.connect(
            lambda _checked=False, p=path: self.retryRequested.emit(p)
        )
        configure(retry_btn, name=self.tr("Retry {file}").format(file=file_name))
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
            self._drop_row(item)
            return
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
        for i, it in enumerate(self._queue_items):
            if it["row"] > row:
                it["row"] -= 1
        self._maybe_emit_queue_completed()

    def _on_clear_finished(self) -> None:
        for item in list(self._queue_items):
            if item.get("state") in TERMINAL_QUEUE_STATES:
                self._drop_row(item)

    def _update_queue_counter(self) -> None:
        """Update the compact header counter (X / Y)."""
        total = len(self._queue_items)
        finished = sum(
            1 for it in self._queue_items
            if it.get("state") in TERMINAL_QUEUE_STATES
        )
        if getattr(self, "_queue_counter", None):
            if total == 0:
                self._queue_counter.setText(self.tr("—  (aucun fichier)"))
            elif finished == 0:
                self._queue_counter.setText(self.tr("→ {total}").format(total=total))
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
        """Toggle Pause / Resume / Stop from the orchestrator state."""
        if not getattr(self, "_pause_btn", None):
            return
        proj = state.get("project") or {}
        status = proj.get("status") if proj else None
        self._pause_btn.setEnabled(status == "running")
        self._resume_btn.setEnabled(status == "paused")
        self._stop_btn.setEnabled(status in ("running", "paused"))

    def _maybe_emit_queue_completed(self) -> None:
        """Emit ``queueCompleted`` when every queue row is terminal."""
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
        item["_status_item"].setText(
            StateLabels.state_label(self.tr, item.get("state", ""))
        )
        stage = str(item.get("current_stage") or "waiting")
        item["_stage_item"].setText(stage.replace("_", " ").title())
        item["_progress_bar"].setValue(max(0, min(100, int(item.get("progress", 0)))))
        detail = (
            item.get("error")
            or item.get("output_path")
            or item.get("project_id")
            or ""
        )
        item["_detail_item"].setText(str(detail))
        item["_detail_item"].setToolTip(str(detail))
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

    # ------------------------------------------------------------------
    # Backward-compatible thin delegates for the pure helpers that used
    # to live here as private methods. The test suite does not call them
    # directly, but main_window.py and other callers may.
    # ------------------------------------------------------------------

    def _progress_from_counts(self, counts: dict[str, Any], total: int) -> int:
        return ProgressMath.progress_from_counts(counts, total)

    def _stage_from_counts(self, counts: dict[str, Any]) -> str | None:
        return ProgressMath.stage_from_counts(counts)

    def _progress_from_stage_event(self, stage: str, percent: Any) -> int:
        return ProgressMath.progress_from_stage_event(stage, percent)

    @classmethod
    def _status_progress_indexes(cls) -> dict[str, int]:
        return ProgressMath.status_progress_indexes()

    @classmethod
    def _stage_for_status(cls, status: str) -> str:
        return ProgressMath.stage_for_status(status)

    def _state_label(self, state: str) -> str:
        return StateLabels.state_label(self.tr, state)

    @staticmethod
    def _status_alias(stage: str) -> str:
        return ProgressMath.status_alias(stage)


# Late import: QLabel is needed by __init__ but lives in QtWidgets.
from PyQt6.QtWidgets import QLabel  # noqa: E402