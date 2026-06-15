"""Virtualized list model for the Review page.

Paginates the backend `GET /chunks?status=…&limit=…&offset=…` endpoint
in chunks of 200 rows. Uses `QAbstractListModel` + lazy `fetchMore`
so a 5000-chunk novel doesn't materialise 5000 widgets at once.
"""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QAbstractListModel, QModelIndex, Qt, QTimer, pyqtSignal


PAGE_SIZE = 200
# Maximum retry attempts on connection failure.
_MAX_INITIAL_RETRIES = 5
# Base delay (s) for exponential backoff on initial fetch.
_INITIAL_RETRY_DELAY = 0.5


class ChunkReviewModel(QAbstractListModel):
    """Lazy, paginated model for the chunk list."""

    errorOccurred = pyqtSignal(str)

    ChunkRole = Qt.ItemDataRole.UserRole + 1

    def __init__(self, client: Any, parent: Any = None) -> None:
        super().__init__(parent)
        self._client = client
        self._items: list[dict[str, Any]] = []
        self._filter: str | None = None
        self._total = 0  # total known (best effort from the backend)
        self._pending = False
        self._end_reached = False
        # Initial-fetch retry state.
        self._initial_retries = _MAX_INITIAL_RETRIES

    # ----- public surface -----

    def set_filter(self, status: str | None) -> None:
        """Change the active status filter; clears the cache."""
        if status == self._filter:
            return
        self._initial_retries = _MAX_INITIAL_RETRIES
        self.beginResetModel()
        self._items.clear()
        self._filter = status
        self._total = 0
        self._end_reached = False
        self.endResetModel()

    def total(self) -> int:
        return self._total

    def chunk_at(self, row: int) -> dict[str, Any] | None:
        if 0 <= row < len(self._items):
            return self._items[row]
        return None

    def refresh(self) -> None:
        """Force a full reload from offset 0."""
        self._initial_retries = _MAX_INITIAL_RETRIES
        self.beginResetModel()
        self._items.clear()
        self._total = 0
        self._end_reached = False
        self.endResetModel()
        if self.rowCount() == 0:
            self.fetchMore()

    # ----- QAbstractListModel API -----

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: B008
        if parent.isValid():
            return 0
        return len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or index.row() >= len(self._items):
            return None
        item = self._items[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            chapter = item.get("chapter_title") or item.get("chapter_id") or ""
            idx = item.get("chunk_index", "")
            status = item.get("status", "")
            preview = (item.get("source_text") or "")[:60].replace("\n", " ")
            return f"{chapter} · {idx} · {status} · {preview}"
        if role == self.ChunkRole:
            return item
        if role == Qt.ItemDataRole.ToolTipRole:
            return item.get("source_text", "")[:300]
        if role == Qt.ItemDataRole.UserRole:
            return item.get("status", "")
        return None

    def canFetchMore(self, parent: QModelIndex = QModelIndex()) -> bool:  # noqa: B008
        if parent.isValid() or self._end_reached or self._pending:
            return False
        return True

    def fetchMore(self, parent: QModelIndex = QModelIndex()) -> None:  # noqa: B008
        if parent.isValid() or self._end_reached or self._pending:
            return
        self._pending = True
        offset = len(self._items)
        try:
            res = self._client.get(
                "/chunks",
                params={
                    "status": self._filter or "",
                    "limit": PAGE_SIZE,
                    "offset": offset,
                },
                timeout=5.0,
            ) or {}
        except Exception as exc:
            self._pending = False
            # On initial load (offset == 0) the backend may not be ready
            # yet — retry with exponential backoff instead of logging a
            # warning.  This prevents the "review model: GET /chunks …"
            # noise at startup.
            if offset == 0 and self._initial_retries > 0:
                self._initial_retries -= 1
                delay = _INITIAL_RETRY_DELAY * (
                    2 ** (_MAX_INITIAL_RETRIES - self._initial_retries - 1)
                )
                QTimer.singleShot(
                    int(delay * 1000),
                    lambda: self.fetchMore() if not self._end_reached else None,
                )
                return
            self.errorOccurred.emit(str(exc))
            return
        items = res.get("items") or []
        total = int(res.get("total") or 0)
        if not items and offset == 0:
            self._end_reached = True
            self._total = total
            self._pending = False
            return
        if not items:
            self._end_reached = True
            self._total = total
            self._pending = False
            return
        start = len(self._items)
        self.beginInsertRows(QModelIndex(), start, start + len(items) - 1)
        self._items.extend(items)
        self.endInsertRows()
        self._total = total or len(self._items)
        if len(items) < PAGE_SIZE:
            self._end_reached = True
        self._pending = False


__all__ = ["ChunkReviewModel", "PAGE_SIZE"]
