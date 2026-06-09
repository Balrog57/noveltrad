"""Activity log widget — collapsible live event stream from the backend.

Receives WebSocket events and renders them with a timestamp and a
level-coloured prefix. Supports a search field and a clickable row
that emits a `chunkActivated(str)` signal when the row is associated
with a chunk_id.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


def _now_hms() -> str:
    return datetime.now().strftime("%H:%M:%S")


class ActivityLogWidget(QWidget):
    """Collapsible live log fed by the backend WebSocket."""

    chunkActivated = pyqtSignal(str)  # chunk_id

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        header_row = QHBoxLayout()
        self._title = QLabel("Activity Log")
        self._title.setStyleSheet("font-weight: 600;")
        header_row.addWidget(self._title)
        header_row.addStretch(1)
        self._toggle = QPushButton("▼")
        self._toggle.setFixedWidth(28)
        self._toggle.setFlat(True)
        self._toggle.clicked.connect(self._toggle_collapsed)
        header_row.addWidget(self._toggle)
        self._count_label = QLabel("0 events")
        self._count_label.setStyleSheet("color: #888;")
        header_row.addWidget(self._count_label)
        layout.addLayout(header_row)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Filter…")
        self._search.textChanged.connect(self._apply_filter)
        self._collapsible = QWidget()
        cbl = QVBoxLayout(self._collapsible)
        cbl.setContentsMargins(0, 0, 0, 0)
        cbl.addWidget(self._search)
        layout.addWidget(self._collapsible)

        self._list = QListWidget()
        self._list.setMaximumHeight(220)
        self._list.setUniformItemSizes(True)
        self._list.itemActivated.connect(self._on_item_activated)
        layout.addWidget(self._list)

        self._items: list[tuple[QListWidgetItem, str, str]] = []
        # (item, text, filter_key)

    # ----- public API -----

    def on_event(self, event: dict[str, Any]) -> None:
        text = self._format(event)
        if not text:
            return
        item = QListWidgetItem(text)
        kind = event.get("type", "")
        colour = self._colour_for(kind)
        if colour:
            from PyQt6.QtGui import QColor

            item.setForeground(QColor(colour))
        item.setData(Qt.ItemDataRole.UserRole, event.get("chunk_id") or "")
        self._list.addItem(item)
        self._list.scrollToBottom()
        filter_key = (text + " " + kind).lower()
        self._items.append((item, text, filter_key))
        self._count_label.setText(f"{len(self._items)} events")

    def clear(self) -> None:
        self._list.clear()
        self._items.clear()
        self._count_label.setText("0 events")

    def _toggle_collapsed(self) -> None:
        visible = not self._collapsible.isVisible() and not self._list.isVisible()
        self._collapsible.setVisible(visible)
        self._list.setVisible(visible)
        self._toggle.setText("▼" if visible else "▲")

    # ----- internals -----

    def _format(self, event: dict[str, Any]) -> str:
        ts = (event.get("timestamp") or "")[:19].split("T")[-1]
        kind = event.get("type", "")
        stage = event.get("stage", "")
        chunk_id = event.get("chunk_id") or ""
        if kind == "log":
            return f"{ts}  {event.get('message', '')}"
        if kind in ("agent_progress", "stage_progress", "chunk_progress"):
            return f"{ts}  {stage}: {event.get('note', '')} ({event.get('percent', 0):.0f}%)"
        if kind == "agent_done":
            payload = event.get("payload") or {}
            note = payload.get("status") or "done"
            n = payload.get("chunk_count")
            if n:
                note += f" ({n} chunks)"
            return f"{ts}  {stage}: {note}"
        if kind == "chunks_submitted":
            return f"{ts}  parser: {event.get('count', 0)} chunks submitted"
        if kind == "hltl_alert":
            return f"{ts}  HITL: {event.get('issue', {}).get('priority', 'issue')} — [View]"
        if kind == "hltl_resolved":
            return f"{ts}  HITL resolved for chunk {chunk_id[:8]}"
        if kind == "agent_error":
            return f"{ts}  ERROR [{stage}]: {event.get('payload', {}).get('message', '')}"
        if kind == "worker_exit":
            return f"{ts}  WORKER EXIT [{event.get('stage', '')}]"
        if kind == "pipeline_started":
            return f"{ts}  pipeline started"
        if kind == "pipeline_paused":
            return f"{ts}  pipeline paused"
        if kind == "pipeline_resumed":
            return f"{ts}  pipeline resumed"
        if kind == "pipeline_stopped":
            return f"{ts}  pipeline stopped"
        if kind == "assemble_triggered":
            return f"{ts}  assembler: writing {event.get('output_path', '')}"
        if kind == "artifact_ready":
            return f"{ts}  output ready: {event.get('output_path', '')}"
        return f"{ts}  {kind}"

    @staticmethod
    def _colour_for(kind: str) -> str | None:
        if kind in ("agent_error", "worker_exit"):
            return "#ff6b6b"
        if kind in ("hltl_alert",):
            return "#ffb86b"
        if kind in ("agent_done", "pipeline_stopped", "artifact_ready"):
            return "#7be395"
        if kind in ("pipeline_paused",):
            return "#ffd166"
        return None

    def _apply_filter(self, text: str) -> None:
        text = text.lower().strip()
        for item, _t, key in self._items:
            if not text or text in key:
                item.setHidden(False)
            else:
                item.setHidden(True)

    def _on_item_activated(self, item: QListWidgetItem) -> None:
        chunk_id = item.data(Qt.ItemDataRole.UserRole)
        if chunk_id:
            self.chunkActivated.emit(str(chunk_id))


__all__ = ["ActivityLogWidget"]
