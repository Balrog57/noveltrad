"""FileCloud — drop zone + multi-file selection badge list.

Replaces the old single-file ``_DropZone`` widget. Accepts a list of
paths from drag-and-drop *or* from a multi-select file dialog, shows
each file as a badge (icon by extension + name + remove button) and
emits a ``filesSelected(list[str])`` signal whenever the set changes.

The widget is reusable — it does not depend on the rest of the
translate workflow — and is intentionally GUI-only (it must not be
imported from the backend).
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..a11y import configure


_SUPPORTED_FILTER = "Documents (*.epub *.docx *.txt *.srt);;All files (*.*)"

_BADGE_ICON = {
    ".epub": "📕",
    ".docx": "📋",
    ".txt": "📝",
    ".srt": "🎬",
}


def _icon_for(path: str) -> str:
    return _BADGE_ICON.get(Path(path).suffix.lower(), "📄")


class FileCloud(QGroupBox):
    """Unified drop + browse + badge list widget."""

    filesSelected = pyqtSignal(list)  # list[str]

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setTitle("")
        self.setObjectName("file-cloud")
        self.setAcceptDrops(True)
        self.setProperty("role", "dropzone")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._selected_paths: list[str] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(6)

        self._icon = QLabel("☁")
        self._icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon.setStyleSheet("font-size: 36pt;")
        outer.addWidget(self._icon)

        self._hint = QLabel(self.tr("Drop files to translate"))
        self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint.setStyleSheet("font-size: 12pt; font-weight: 600;")
        outer.addWidget(self._hint)

        self._sub = QLabel(self.tr("TXT, EPUB, SRT, DOCX — up to 10 files"))
        self._sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._sub.setProperty("role", "muted")
        outer.addWidget(self._sub)

        # List of selected files (replaces the old _path_label).
        self._list = QListWidget()
        self._list.setMaximumHeight(120)
        self._list.setUniformItemSizes(True)
        configure(
            self._list,
            name="Selected files",
            description="List of files queued for translation. Use the X button to remove one.",
        )
        outer.addWidget(self._list)

        # Counter + Browse button row.
        row = QHBoxLayout()
        self._counter = QLabel("")
        self._counter.setProperty("role", "muted")
        row.addWidget(self._counter)
        row.addStretch(1)
        self._browse = QPushButton(self.tr("Browse…"))
        self._browse.setProperty("role", "primary")
        self._browse.clicked.connect(self._open_dialog)
        configure(self._browse, name="Browse files")
        row.addWidget(self._browse)
        outer.addLayout(row)

        self._refresh_empty_state()

    # ----- public API -----

    def selected_paths(self) -> list[str]:
        return list(self._selected_paths)

    def clear(self) -> None:
        self._selected_paths = []
        self._list.clear()
        self._refresh_empty_state()
        self.filesSelected.emit([])

    def add_paths(self, paths: Iterable[str]) -> None:
        added = False
        for raw in paths:
            if not raw:
                continue
            # local files only; remote urls are silently dropped
            try:
                p = str(Path(raw))
            except (TypeError, ValueError):
                continue
            if p in self._selected_paths:
                continue
            self._selected_paths.append(p)
            row = QListWidgetItem()
            row.setData(Qt.ItemDataRole.UserRole, p)
            row.setToolTip(p)
            self._list.addItem(row)
            # Embed a small custom widget per row that shows the
            # badge label AND the remove button. Using setItemWidget
            # with a single QPushButton would hide the item's text in
            # QListWidget, so we ship a row widget instead.
            self._attach_remove_button(row, p)
            added = True
        if added:
            self._refresh_empty_state()
            self.filesSelected.emit(list(self._selected_paths))

    def _attach_remove_button(self, row: QListWidgetItem, path: str) -> None:
        from PyQt6.QtWidgets import (
            QHBoxLayout,
            QLabel,
            QPushButton,
            QWidget,
        )  # local import: keep top stable

        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(6)
        label = QLabel(f"{_icon_for(path)}  {Path(path).name}")
        label.setToolTip(path)
        layout.addWidget(label, 1)
        btn = QPushButton(self.tr("✕"))
        btn.setFixedSize(28, 24)
        btn.setFlat(True)
        btn.setToolTip(self.tr("Remove this file"))
        btn.clicked.connect(lambda _checked=False, p=path: self.remove_path(p))
        layout.addWidget(btn, 0)
        # The list view sizes items by the widget's sizeHint; we need
        # at least one fixed row height for the embedded widget to
        # render correctly.
        row.setSizeHint(widget.sizeHint())
        self._list.setItemWidget(row, widget)

    def remove_path(self, path: str) -> None:
        if path not in self._selected_paths:
            return
        self._selected_paths.remove(path)
        for i in range(self._list.count()):
            it = self._list.item(i)
            if it and it.data(Qt.ItemDataRole.UserRole) == path:
                # Detach the embedded button (Qt would crash on takeItem
                # if the widget is still parented to the list).
                self._list.removeItemWidget(it)
                self._list.takeItem(i)
                break
        self._refresh_empty_state()
        self.filesSelected.emit(list(self._selected_paths))

    # ----- drag & drop -----

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._set_active(True)

    def dragLeaveEvent(self, event) -> None:  # noqa: ANN001 - Qt signature
        self._set_active(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        self._set_active(False)
        paths = [u.toLocalFile() for u in urls if u.isLocalFile()]
        if paths:
            self.add_paths(paths)
            event.acceptProposedAction()

    def mousePressEvent(self, event) -> None:  # noqa: ANN001 - Qt signature
        if event.button() == Qt.MouseButton.LeftButton:
            self._open_dialog()
        super().mousePressEvent(event)

    # ----- internals -----

    def _open_dialog(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            self.tr("Select files to translate"),
            "",
            _SUPPORTED_FILTER,
        )
        if paths:
            self.add_paths(paths)

    def _set_active(self, active: bool) -> None:
        self.setProperty("active", "true" if active else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def _refresh_empty_state(self) -> None:
        n = len(self._selected_paths)
        if n == 0:
            self._icon.setText("☁")
            self._hint.setText(self.tr("Drop files to translate"))
            self._sub.setVisible(True)
            self._counter.setText("")
        else:
            self._icon.setText("📄")
            self._hint.setText(
                self.tr("{n} file(s) selected").format(n=n)
            )
            self._sub.setVisible(False)
            self._counter.setText(self.tr("{n} ready").format(n=n))


__all__ = ["FileCloud"]
