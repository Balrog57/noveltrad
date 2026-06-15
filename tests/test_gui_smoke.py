"""GUI smoke tests, run offscreen (no real display needed).

These tests instantiate the `MainWindow` and the design-system helpers
under `QT_QPA_PLATFORM=offscreen`. They verify:

  * the 5 pages are mounted in the stacked widget,
  * the three theme names apply without raising,
  * global shortcuts are bound,
  * QSettings round-trips the geometry / current page,
  * the responsive drawer activates below 900 px and deactivates above,
  * the WebSocket event debouncer coalesces bursts and forwards one
    batch to the listener,
  * the `ChunkReviewModel` paginates from a fake backend.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path


# Must be set before any Qt import.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import (  # noqa: E402
    Q_ARG,
    QCoreApplication,
    QEvent,
    QMetaObject,
    QSettings,
    Qt,
    QTimer,
)
from PyQt6.QtGui import QKeyEvent  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from src.gui.a11y import GLOBAL_SHORTCUTS  # noqa: E402
from src.gui.design_system import (  # noqa: E402
    DARK,
    HIGH_CONTRAST,
    LIGHT,
    PALETTES,
    get_palette,
)
from src.gui.main_window import DRAWER_BREAKPOINT  # noqa: E402
from src.gui.theme import VALID_THEMES, ThemeManager  # noqa: E402
from src.gui.widgets.event_debouncer import EventDebouncer  # noqa: E402
from src.gui.dialogs.update_dialog import UpdateDialog  # noqa: E402
from src.gui.updater import UpdateInfo, Updater  # noqa: E402


def _ensure_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    # Ensure each test starts from a known QSettings scope so they
    # don't leak geometry between runs on developer machines.
    QCoreApplication.setOrganizationName("NovelTrad")
    QCoreApplication.setApplicationName("NovelTrad-tests")
    return app


class DesignSystemTests(unittest.TestCase):
    def test_palettes_complete(self) -> None:
        for name in VALID_THEMES:
            self.assertIn(name, PALETTES)
            self.assertIs(PALETTES[name], get_palette(name))

    def test_tokens_build_stylesheet(self) -> None:
        from src.gui.design_system import DesignTokens

        tokens = DesignTokens(palette=DARK)
        ss = tokens.stylesheet()
        for needle in ("QPushButton", "QListView", "QProgressBar", "QStatusBar"):
            self.assertIn(needle, ss)
        # Light and high-contrast must also produce non-empty output.
        self.assertIn("background-color", DesignTokens(palette=LIGHT).stylesheet())
        self.assertIn(
            "background-color", DesignTokens(palette=HIGH_CONTRAST).stylesheet()
        )


class ThemeManagerTests(unittest.TestCase):
    def test_cycle_and_apply(self) -> None:
        app = _ensure_app()
        tm = ThemeManager.instance()
        for name in VALID_THEMES:
            tm.apply(app, name)
            self.assertEqual(tm.current, name)
            self.assertIn("QPushButton", app.styleSheet())
        # After cycling, the manager should have moved to the next theme.
        start = tm.current
        nxt = tm.cycle(app)
        self.assertNotEqual(start, nxt)
        self.assertIn(nxt, VALID_THEMES)


class UpdateDialogTests(unittest.TestCase):
    def test_download_callbacks_are_qt_slots(self) -> None:
        app = _ensure_app()
        dialog = UpdateDialog(
            Updater("4.1.0"),
            UpdateInfo(
                version="4.1.5",
                tag="v4.1.5",
                release_date="",
                body="",
                download_url="https://example.com/setup.exe",
            ),
        )
        meta = dialog.metaObject()
        self.assertGreaterEqual(meta.indexOfSlot("_set_progress(int)"), 0)
        self.assertGreaterEqual(meta.indexOfSlot("_on_download_finished()"), 0)

        QMetaObject.invokeMethod(
            dialog,
            "_set_progress",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(int, 42),
        )
        app.processEvents()
        self.assertEqual(dialog._progress.value(), 42)


class MainWindowSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _ensure_app()
        # Use a temporary QSettings store so we don't clobber user data.
        cls._tmp = tempfile.mkdtemp()
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(
            QSettings.Format.IniFormat,
            QSettings.Scope.UserScope,
            cls._tmp,
        )

    def setUp(self) -> None:
        # Reset theme between tests.
        from src.gui import main_window as mw

        mw.QApplication_or_holder = mw.QApplication_or_holder  # touch
        from src.gui.main_window import MainWindow

        self.w = MainWindow()

    def tearDown(self) -> None:
        if getattr(self, "w", None) is not None:
            self.w.close()
            self.w.deleteLater()

    def test_five_pages_mounted(self) -> None:
        self.assertEqual(self.w._stack.count(), 5)

    def test_responsive_drawer_under_breakpoint(self) -> None:
        # Width < breakpoint: sidebar must hide.
        self.w._apply_responsive_mode(DRAWER_BREAKPOINT - 1)
        self.assertFalse(self.w._drawer_open)

    def test_responsive_full_above_breakpoint(self) -> None:
        # Width >= breakpoint: sidebar must show.
        self.w._drawer_open = False
        self.w._apply_responsive_mode(DRAWER_BREAKPOINT + 1)
        self.assertTrue(self.w._drawer_open)

    def test_drawer_toggle(self) -> None:
        # Above breakpoint, the hamburger toggles the sidebar.
        self.w._apply_responsive_mode(DRAWER_BREAKPOINT + 100)
        self.assertTrue(self.w._drawer_open)
        self.w._toggle_drawer()
        self.assertFalse(self.w._drawer_open)
        self.w._toggle_drawer()
        self.assertTrue(self.w._drawer_open)

    def test_qsettings_round_trip(self) -> None:
        # The MainWindow restores the current page from QSettings on
        # init. Change the current page, close, and re-instantiate.
        self.w._sidebar.setCurrentRow(2)
        # Persist synchronously (closeEvent already does this).
        self.w._settings.setValue(
            "MainWindow/currentPage", self.w._sidebar.currentRow()
        )
        self.w._settings.sync()
        self.w.close()
        self.w.deleteLater()
        self.w = None  # type: ignore[assignment]
        from src.gui.main_window import MainWindow

        w2 = MainWindow()
        try:
            QCoreApplication.processEvents()
            self.assertEqual(w2._sidebar.currentRow(), 2)
        finally:
            w2.close()
            w2.deleteLater()

    def test_global_shortcuts_bound(self) -> None:
        from PyQt6.QtGui import QShortcut

        shortcuts = self.w.findChildren(QShortcut)
        self.assertGreaterEqual(
            len(shortcuts),
            5,
            f"expected at least 5 QShortcut children, found {len(shortcuts)}",
        )
        sequences = sorted(sc.key().toString() for sc in shortcuts)
        for needed in ("Ctrl+O", "Ctrl+R", "Ctrl+,", "F1", "Ctrl+Q", "Ctrl+Shift+T"):
            self.assertIn(needed, sequences, f"missing shortcut {needed}")


class EventDebouncerTests(unittest.TestCase):
    def test_collapses_progress_per_chunk_stage(self) -> None:
        app = _ensure_app()
        received: list[list[dict]] = []

        def slot(batch: list[dict]) -> None:
            received.append(batch)

        d = EventDebouncer(slot, interval_ms=20)
        # Burst: 3 progress events for the same (chunk, stage), 1 progress
        # for another chunk, then a non-progress event.
        d.push({"type": "agent_progress", "chunk_id": "c1", "stage": "fast_translator"})
        d.push({"type": "agent_progress", "chunk_id": "c1", "stage": "fast_translator"})
        d.push({"type": "agent_progress", "chunk_id": "c1", "stage": "fast_translator"})
        d.push({"type": "agent_progress", "chunk_id": "c2", "stage": "fast_translator"})
        d.push({"type": "agent_done", "chunk_id": "c1", "stage": "fast_translator"})
        # Wait for the timer to flush.
        loop_done = {"ok": False}

        def check() -> None:
            if received:
                loop_done["ok"] = True
                QTimer.singleShot(0, app.quit)

        QTimer.singleShot(150, check)
        QTimer.singleShot(2000, app.quit)
        app.exec()
        self.assertTrue(loop_done["ok"], "debouncer did not flush in time")
        flat = [ev for batch in received for ev in batch]
        types = [ev["type"] for ev in flat]
        # 1 collapsed c1 progress + 1 c2 progress + 1 agent_done = 3 events
        self.assertEqual(types.count("agent_progress"), 2)
        self.assertEqual(types.count("agent_done"), 1)
        self.assertEqual(d.total_received, 5)
        self.assertEqual(d.total_flushed, 3)


class ActivityLogQueueEventTests(unittest.TestCase):
    def test_formats_queue_events(self) -> None:
        app = _ensure_app()
        from src.gui.widgets.activity_log import ActivityLogWidget

        log = ActivityLogWidget()
        try:
            log.on_event(
                {
                    "type": "project_queued",
                    "project_id": "p2",
                    "queue_position": 2,
                }
            )
            log.on_event(
                {
                    "type": "project_started_from_queue",
                    "project_id": "p2",
                    "queue_remaining": 1,
                }
            )
            log.on_event({"type": "project_queue_failed", "project_id": "p3"})
            texts = [log._list.item(i).text() for i in range(log._list.count())]
            self.assertIn("queued project p2", texts[0])
            self.assertIn("started queued project p2", texts[1])
            self.assertIn("queue failed for project p3", texts[2])
        finally:
            log.deleteLater()
            app.processEvents()


class ReviewModelTests(unittest.TestCase):
    def test_paginates_from_fake_client(self) -> None:
        app = _ensure_app()

        class FakeClient:
            def __init__(self) -> None:
                self.calls: list[dict] = []

            def get(self, path, timeout=5.0, params=None):
                self.calls.append(params or {})
                offset = int((params or {}).get("offset", 0))
                limit = int((params or {}).get("limit", 200))
                # Two pages of 200 + 50 = 450 total.
                page_start = offset
                page_end = min(offset + limit, 450)
                items = [
                    {
                        "id": f"c{i}",
                        "chapter_id": "ch1",
                        "chapter_title": "Chapter 1",
                        "chunk_index": i,
                        "source_text": f"text {i}",
                        "status": "polished",
                    }
                    for i in range(page_start, page_end)
                ]
                return {"items": items, "total": 450, "limit": limit, "offset": offset}

        from src.gui.tabs.review_model import ChunkReviewModel

        client = FakeClient()
        model = ChunkReviewModel(client)
        self.assertEqual(model.rowCount(), 0)
        # First fetchMore brings 200 rows.
        model.fetchMore()
        self.assertEqual(model.rowCount(), 200)
        # Second fetchMore brings the next 200.
        model.fetchMore()
        self.assertEqual(model.rowCount(), 400)
        # Third fetchMore brings 50 and sets end_reached.
        model.fetchMore()
        self.assertEqual(model.rowCount(), 450)
        self.assertFalse(model.canFetchMore())
        # Inspect calls: offsets are 0, 200, 400.
        offsets = [c["offset"] for c in client.calls]
        self.assertEqual(offsets, [0, 200, 400])


class TranslateTabNavigationTests(unittest.TestCase):
    def test_choose_files_button_returns_to_select_and_blocks_auto_pipeline_jump(self) -> None:
        app = _ensure_app()
        from src.gui.tabs.translate_tab import TranslateTab

        tab = TranslateTab()
        try:
            state = {
                "state_store": {
                    "chunks_total": 1,
                    "chunks_by_status": {"polished": 1},
                }
            }
            tab.update_pipeline_state(state)
            self.assertEqual(tab._stack.currentIndex(), 1)
            tab._go_to_select()
            self.assertEqual(tab._stack.currentIndex(), 0)
            tab.update_pipeline_state(state)
            self.assertEqual(tab._stack.currentIndex(), 0)
        finally:
            tab.deleteLater()
            app.processEvents()

    def test_start_creates_queue_rows_and_emits_one_project_per_file(self) -> None:
        app = _ensure_app()
        from src.gui.tabs.translate_tab import TranslateTab

        tab = TranslateTab()
        captured: list[dict] = []
        tab.startRequested.connect(lambda payload: captured.append(dict(payload)))
        try:
            paths = [str(Path(f"C:/tmp/book_{i}.txt")) for i in range(12)]
            tab._cloud.add_paths(paths)
            tab._on_start()
            self.assertEqual(tab._queue_table.rowCount(), 12)
            self.assertEqual(len(captured), 12)
            self.assertEqual([c["source_paths"][0] for c in captured], paths)
            self.assertEqual(tab._stack.currentIndex(), 1)
        finally:
            tab.deleteLater()
            app.processEvents()

    def test_queue_updates_from_project_response_events_and_artifact(self) -> None:
        app = _ensure_app()
        from src.gui.tabs.translate_tab import TranslateTab

        tab = TranslateTab()
        try:
            path = str(Path("C:/tmp/book.txt"))
            payload = {"source_path": path, "source_paths": [path]}
            tab._add_queue_item(path)
            tab.on_project_created(payload, {"project_id": "p1", "queue_position": 0})
            self.assertEqual(tab._queue_items[0]["state"], "running")
            tab.on_pipeline_event(
                {
                    "type": "agent_progress",
                    "project_id": "p1",
                    "stage": "fast_translator",
                    "percent": 50,
                }
            )
            self.assertEqual(tab._queue_items[0]["current_stage"], "fast_translator")
            self.assertGreater(tab._queue_items[0]["progress"], 0)
            tab.on_artifact_ready("C:/tmp/out.txt")
            self.assertEqual(tab._queue_items[0]["state"], "done")
            self.assertEqual(tab._queue_items[0]["progress"], 100)
            self.assertIn("out.txt", tab._queue_items[0]["_detail_item"].text())
        finally:
            tab.deleteLater()
            app.processEvents()

    def test_pipeline_state_updates_active_file_progress(self) -> None:
        app = _ensure_app()
        from src.gui.tabs.translate_tab import TranslateTab

        tab = TranslateTab()
        try:
            path = str(Path("C:/tmp/book.txt"))
            payload = {"source_path": path, "source_paths": [path]}
            tab.on_project_created(payload, {"project_id": "p1", "queue_position": 0})
            tab.update_pipeline_state(
                {
                    "project": {
                        "project_id": "p1",
                        "status": "running",
                        "source_path": path,
                        "source_paths": [path],
                    },
                    "state_store": {
                        "chunks_total": 2,
                        "chunks_by_status": {"fast_translated": 1, "polished": 1},
                    },
                    "project_queue": [],
                }
            )
            item = tab._queue_items[0]
            self.assertEqual(item["current_stage"], "llm_polisher")
            self.assertGreater(item["progress"], 0)
            self.assertEqual(tab._stack.currentIndex(), 1)
        finally:
            tab.deleteLater()
            app.processEvents()


if __name__ == "__main__":
    unittest.main()
