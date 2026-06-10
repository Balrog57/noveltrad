"""WebSocket event debouncer.

The orchestrator can emit bursts of 50+ events per second (every
`agent_progress` for every chunk). Repainting on every event would
choke the GUI thread. `EventDebouncer` collects events into a deque
and flushes them in batches every 100 ms via a `QTimer`.

It also collapses `agent_progress` events into the latest one per
(chunk_id, stage) pair so the activity log and pipeline cards can
update with at most one row per chunk per tick.
"""

from __future__ import annotations

from collections import deque
from typing import Any, Callable

from PyQt6.QtCore import QObject, QTimer


class EventDebouncer(QObject):
    """Batch WebSocket events for the GUI thread."""

    def __init__(
        self,
        flush_slot: Callable[[list[dict[str, Any]]], None],
        parent: QObject | None = None,
        interval_ms: int = 100,
    ) -> None:
        super().__init__(parent)
        self._slot = flush_slot
        self._interval_ms = interval_ms
        self._buffer: deque[dict[str, Any]] = deque(maxlen=4096)
        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self._flush)
        self._timer.start()
        # Total events seen since startup, for tests / diagnostics.
        self.total_received = 0
        self.total_flushed = 0

    def push(self, event: dict[str, Any]) -> None:
        self._buffer.append(event)
        self.total_received += 1

    def flush_now(self) -> None:
        """Force-flush the buffer (used on shutdown)."""
        self._flush()

    def _flush(self) -> None:
        if not self._buffer:
            return
        batch: list[dict[str, Any]] = []
        seen_progress: dict[tuple[str, str | None], dict[str, Any]] = {}
        while self._buffer:
            ev = self._buffer.popleft()
            if ev.get("type") == "agent_progress":
                key = (ev.get("chunk_id") or "", ev.get("stage") or "")
                seen_progress[key] = ev  # keep the last one
            else:
                # Flush any progress seen so far first, in order.
                if seen_progress:
                    batch.extend(seen_progress.values())
                    seen_progress.clear()
                batch.append(ev)
        if seen_progress:
            batch.extend(seen_progress.values())
        if batch:
            self._slot(batch)
            self.total_flushed += len(batch)


__all__ = ["EventDebouncer"]
