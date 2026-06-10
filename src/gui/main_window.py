"""MainWindow for NovelTrad v4 — sidebar + stacked pages layout.

Layout:

   [📚 NovelTrad]              ● LLM: Ollama …   [🌙] [☰]
   ────────────────────────────────────────────────────────
   [ Translate  ] ┌──────────────────────────────────────┐
   [ Projects  ]  │   page content                       │
   [ Glossaries]  │   (QStackedWidget)                   │
   [ Files     ]  │                                      │
   [ Settings  ]  │                                      │
   ───────────────┴──────────────────────────────────────┘
   Activity Log (collapsible, fed by WebSocket)

Responsive: below 900 px the sidebar collapses into a drawer
toggled by the hamburger button in the header. State is persisted
via QSettings on `closeEvent` and restored on `__init__`.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QSettings, Qt, QTimer
from PyQt6.QtGui import QAction, QCloseEvent, QKeySequence
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from src.gui.a11y import GLOBAL_SHORTCUTS, bind_shortcut, configure
from src.gui.app_config import ConfigManager
from src.gui.backend_client import BackendClient, BackendError
from src.gui.dialogs.chunk_detail_dialog import ChunkDetailDialog
from src.gui.dialogs.hitl_popup import HITLPopup
from src.gui.dialogs.update_dialog import UpdateDialog
from src.gui.notifier import Notifier
from src.gui.tabs.files_tab import FilesTab
from src.gui.tabs.glossaries_tab import GlossariesTab
from src.gui.tabs.settings_tab import SettingsTab
from src.gui.tabs.translate_tab import TranslateTab
from src.gui.theme import VALID_THEMES, ThemeManager
from src.gui.updater import Updater, is_skipped
from src.gui.widgets.activity_log import ActivityLogWidget
from src.gui.widgets.event_debouncer import EventDebouncer

logger = logging.getLogger(__name__)


SIDEBAR_ITEMS: tuple[tuple[str, str], ...] = (
    ("translate", "Translate"),
    ("projects", "Projects"),
    ("glossaries", "Glossaries"),
    ("files", "Files"),
    ("settings", "Settings"),
)

DRAWER_BREAKPOINT = 700


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NovelTrad")
        self.resize(1100, 760)

        self._config = ConfigManager()
        self._config.apply_environment()
        backend_url = os.environ.get("NOVELTRAD_BACKEND", "http://127.0.0.1:8765")
        self._client = BackendClient(backend_url)
        self._backend_proc: subprocess.Popen | None = None
        self._active_hitl: dict[str, HITLPopup] = {}
        self._notifier = Notifier(self)
        # Auto-updater. We never auto-update when the env var disables
        # it or when we're running from the dev checkout (Updater
        # short-circuits in that case).
        import src as _src_pkg

        self._updater = Updater(current_version=_src_pkg.__version__)
        self._pending_update_dialog: UpdateDialog | None = None

        # Apply theme via ThemeManager (persisted in QSettings).
        self._theme = ThemeManager.instance()
        self._settings = QSettings()
        self._theme.restore_from(self._settings, QApplication_or_holder(self))

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # --- header ---
        header = QWidget()
        hbox = QHBoxLayout(header)
        hbox.setContentsMargins(12, 6, 12, 6)
        self._hamburger = QPushButton("☰")
        self._hamburger.setFixedWidth(36)
        self._hamburger.clicked.connect(self._toggle_drawer)
        configure(self._hamburger, name="Toggle sidebar drawer")
        hbox.addWidget(self._hamburger)

        title = QLabel("📚  NovelTrad")
        title.setProperty("role", "title")
        hbox.addWidget(title)
        hbox.addStretch(1)
        self._llm_badge = QLabel("● LLM: …")
        self._llm_badge.setProperty("role", "muted")
        hbox.addWidget(self._llm_badge)
        self._theme_btn = QPushButton("🌙")
        self._theme_btn.setFixedWidth(36)
        self._theme_btn.clicked.connect(self._cycle_theme)
        configure(self._theme_btn, name="Cycle theme", tooltip="Switch theme (Ctrl+Shift+T)")
        hbox.addWidget(self._theme_btn)
        root.addWidget(header)

        # --- sidebar + stacked pages in a splitter ---
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._sidebar = QListWidget()
        for _key, label in SIDEBAR_ITEMS:
            item = QListWidgetItem(label)
            self._sidebar.addItem(item)
        self._sidebar.setFixedWidth(200)
        self._sidebar.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        configure(self._sidebar, name="Navigation")
        self._sidebar.currentRowChanged.connect(self._on_sidebar_changed)

        self._stack = QStackedWidget()
        self._translate_tab = TranslateTab(
            default_target="fr", client=self._client
        )
        self._translate_tab.startRequested.connect(self._on_start_translation)
        self._translate_tab.replayHltlRequested.connect(self._on_replay_hltl)
        self._translate_tab.assembleRequested.connect(self._on_assemble_requested)
        self._stack.addWidget(self._translate_tab)
        self._projects_tab = self._build_projects_placeholder()
        self._stack.addWidget(self._projects_tab)
        self._glossaries_tab = GlossariesTab(self._client)
        self._stack.addWidget(self._glossaries_tab)
        self._files_tab = FilesTab(self._client)
        self._files_tab.chunkActivated.connect(self._show_chunk_detail)
        self._stack.addWidget(self._files_tab)
        self._settings_tab = SettingsTab()
        self._settings_tab.checkForUpdatesRequested.connect(
            self._on_manual_check_for_updates
        )
        self._stack.addWidget(self._settings_tab)

        self._splitter.addWidget(self._sidebar)
        self._splitter.addWidget(self._stack)
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setCollapsible(0, True)
        root.addWidget(self._splitter, 1)

        # --- activity log ---
        self._activity = ActivityLogWidget()
        self._activity.chunkActivated.connect(self._show_chunk_detail)
        root.addWidget(self._activity)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Starting backend…")

        # WebSocket event debouncer.
        self._debouncer = EventDebouncer(self._on_event_batch, parent=self)

        # Install global shortcuts.
        self._install_shortcuts()

        # Start backend subprocess (idempotent if already running).
        self._start_backend()
        # Periodically refresh LLM badge + status.
        self._timer = QTimer(self)
        self._timer.setInterval(2000)
        self._timer.timeout.connect(self._refresh_status)
        self._timer.start()
        QTimer.singleShot(500, self._post_startup)
        # Restore layout.
        self._restore_layout()
        # Apply initial responsive mode once the window is actually
        # shown (resizeEvent won't fire on a hidden widget). We default
        # to "full sidebar" until the first show; the resizeEvent will
        # then re-evaluate against the real geometry.
        self._drawer_open = True
        self._sidebar.setVisible(True)
        self._splitter.setSizes([200, max(400, self.width() - 200)])

        # Background auto-update check, fires once the UI is settled.
        QTimer.singleShot(3000, self._check_for_updates)

    # ----- responsive -----

    def resizeEvent(self, event) -> None:  # noqa: ANN001 - Qt signature
        super().resizeEvent(event)
        self._apply_responsive_mode(event.size().width())

    def _apply_responsive_mode(self, width: int) -> None:
        drawer = width < DRAWER_BREAKPOINT
        if drawer:
            self._splitter.setSizes([0, width])
            self._sidebar.setVisible(False)
            self._drawer_open = False
        else:
            self._sidebar.setVisible(True)
            self._drawer_open = True
            if self._splitter.sizes()[0] == 0:
                self._splitter.setSizes([200, max(400, width - 200)])

    def _toggle_drawer(self) -> None:
        # Manual user action (hamburger click). Always toggles the
        # sidebar visibility, regardless of the responsive breakpoint.
        if self._drawer_open:
            self._sidebar.setVisible(False)
            self._drawer_open = False
            self._splitter.setSizes([0, max(400, self.width())])
        else:
            self._sidebar.setVisible(True)
            self._drawer_open = True
            self._splitter.setSizes(
                [200, max(400, self.width() - 200)]
            )

    # ----- shortcuts -----

    def _install_shortcuts(self) -> None:
        bind_shortcut(self, "Ctrl+O", self._action_open_file)
        bind_shortcut(self, "Ctrl+R", self._action_rerun)
        bind_shortcut(self, "Ctrl+,", self._action_settings)
        bind_shortcut(self, "F1", self._action_help)
        bind_shortcut(self, "Ctrl+Q", self.close)
        bind_shortcut(self, "Ctrl+Shift+T", self._cycle_theme)
        bind_shortcut(self, "Esc", self._action_close_overlay)

    def _action_open_file(self) -> None:
        if hasattr(self._translate_tab, "_drop"):
            self._translate_tab._drop._open_dialog()  # type: ignore[attr-defined]

    def _action_rerun(self) -> None:
        # Best-effort: replay pending HITL counts as a "rerun" of the
        # most stuck chunks.
        self._on_replay_hltl()

    def _action_settings(self) -> None:
        idx = next(
            (i for i, (k, _) in enumerate(SIDEBAR_ITEMS) if k == "settings"), 0
        )
        self._sidebar.setCurrentRow(idx)
        self._stack.setCurrentIndex(idx)

    def _action_help(self) -> None:
        lines = ["Keyboard shortcuts:"]
        for spec in GLOBAL_SHORTCUTS:
            lines.append(f"  {spec.sequence:<14} {spec.label}")
        QMessageBox.information(self, "Help", "\n".join(lines))

    def _action_close_overlay(self) -> None:
        # Close any active HITL popup.
        if self._active_hitl:
            for dlg in list(self._active_hitl.values()):
                dlg.reject()
        elif self._sidebar.isVisible() and self.width() < DRAWER_BREAKPOINT:
            self._toggle_drawer()

    # ----- theme -----

    def _cycle_theme(self) -> None:
        from PyQt6.QtWidgets import QApplication

        new_name = self._theme.cycle(QApplication.instance())  # type: ignore[arg-type]
        self._theme.save_to(self._settings)
        self._theme_btn.setText({"light": "☀", "dark": "🌙", "high_contrast": "🔆"}[new_name])
        self.statusBar().showMessage(f"Theme: {new_name}", 2000)

    # ----- projects placeholder -----

    def _build_projects_placeholder(self) -> QWidget:
        page = QFrame()
        page.setProperty("role", "card")
        v = QVBoxLayout(page)
        v.setContentsMargins(24, 24, 24, 24)
        title = QLabel("Recent projects")
        title.setProperty("role", "title")
        v.addWidget(title)
        hint = QLabel(
            "Projects will appear here as you translate. "
            "Each entry shows source, target, date and a quick re-open action."
        )
        hint.setProperty("role", "muted")
        hint.setWordWrap(True)
        v.addWidget(hint)
        v.addStretch(1)
        configure(page, name="Recent projects", description="List of past translation runs.")
        return page

    # ----- backend lifecycle -----

    def _start_backend(self) -> None:
        try:
            if self._client.health().get("ok"):
                self.statusBar().showMessage("Backend connected.")
                return
        except Exception:
            pass
        try:
            env = os.environ.copy()
            self._config.apply_environment()
            env.update(os.environ)
            env.setdefault("NOVELTRAD_HOST", "127.0.0.1")
            env.setdefault("NOVELTRAD_PORT", "8765")
            backend_cmd = [
                sys.executable,
                "-m",
                "src.backend.server",
                "--host",
                "127.0.0.1",
                "--port",
                "8765",
            ]
            if getattr(sys, "frozen", False):
                backend_cmd = [
                    sys.executable,
                    "--backend",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8765",
                ]
            self._backend_proc = subprocess.Popen(  # noqa: S603
                backend_cmd,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=str(Path(__file__).resolve().parents[2]),
            )
        except Exception as exc:
            QMessageBox.warning(
                self, "Backend", f"Could not start backend subprocess: {exc}"
            )
            return

        def _wait() -> None:
            if self._client.wait_ready(timeout_s=15.0):
                QTimer.singleShot(0, lambda: self.statusBar().showMessage("Backend ready."))
            else:
                QTimer.singleShot(
                    0,
                    lambda: self.statusBar().showMessage("Backend did not respond."),
                )

        import threading

        threading.Thread(target=_wait, daemon=True).start()

    def _post_startup(self) -> None:
        try:
            self._client.open_websocket(self._on_ws_event)
        except Exception as exc:
            logger.warning("WebSocket open failed: %s", exc)
        self._refresh_status()

    def _on_ws_event(self, event: dict[str, Any]) -> None:
        # Marshal to GUI thread and into the debouncer.
        self._debouncer.push(event)

    def _on_event_batch(self, batch: list[dict[str, Any]]) -> None:
        for event in batch:
            self._handle_event(event)

    def _handle_event(self, event: dict[str, Any]) -> None:
        self._activity.on_event(event)
        kind = event.get("type")
        if kind == "hltl_alert":
            self._show_hitl(event)
            self._notifier.notify(
                "HITL needed",
                f"Stage {event.get('stage', '?')}: {(event.get('issue') or {}).get('summary', '')}",
                level="warning",
            )
        elif kind == "agent_done":
            if self._files_tab is not None:
                self._files_tab.refresh()
        elif kind == "artifact_ready":
            self._translate_tab.on_artifact_ready(event.get("output_path", ""))
        elif kind == "pipeline_started":
            self.statusBar().showMessage("Pipeline started.")
        elif kind == "hltl_unroutable":
            self.statusBar().showMessage(
                f"HITL not routed: {event.get('reason', '?')}", 5000
            )

    def _show_hitl(self, event: dict[str, Any]) -> None:
        rid = event.get("request_id", "")
        if not rid or rid in self._active_hitl:
            return
        dlg = HITLPopup(
            request_id=rid,
            chunk_id=event.get("chunk_id", ""),
            stage=event.get("stage", ""),
            issue=event.get("issue") or {},
            client=self._client,
            parent=self,
        )
        self._active_hitl[rid] = dlg
        dlg.finished.connect(lambda _r, k=rid: self._active_hitl.pop(k, None))
        dlg.show()

    def _show_chunk_detail(self, chunk_id: str) -> None:
        if not chunk_id:
            return
        dlg = ChunkDetailDialog(chunk_id, self._client, parent=self)
        dlg.exec()

    # ----- actions -----

    def _on_start_translation(self, payload: dict[str, Any]) -> None:
        try:
            res = self._client.post(
                "/projects",
                body={
                    "project_dir": payload.get("project_dir") or "./projects",
                    "source_path": payload["source_path"],
                    "source_lang": payload.get("source_lang", "auto"),
                    "target_lang": payload.get("target_lang", "fr"),
                    "parse": True,
                },
                timeout=10.0,
            )
        except BackendError as exc:
            QMessageBox.warning(self, "Start failed", str(exc))
            return
        self._activity.on_event(
            {
                "type": "log",
                "message": f"Project created: {res.get('project_id')}",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
        )
        self.statusBar().showMessage(f"Project {res.get('project_id')} running…")

    def _on_replay_hltl(self) -> None:
        try:
            res = self._client.post("/orchestrator/hltl/replay", timeout=5.0) or {}
        except BackendError as exc:
            self.statusBar().showMessage(f"Replay failed: {exc}", 4000)
            return
        routed = res.get("routed", 0)
        skipped = res.get("skipped", 0)
        self.statusBar().showMessage(
            f"HITL replay: {routed} routed, {skipped} skipped", 4000
        )

    def _on_assemble_requested(self, fmt: str) -> None:
        try:
            res = self._client.post(
                "/projects/assemble",
                body={"format": fmt},
                timeout=10.0,
            ) or {}
        except BackendError as exc:
            QMessageBox.warning(self, "Assemble failed", str(exc))
            return
        if res.get("output_path"):
            self.statusBar().showMessage(
                f"Output: {res['output_path']}", 5000
            )

    def _on_sidebar_changed(self, idx: int) -> None:
        if idx < 0 or idx >= self._stack.count():
            return
        self._stack.setCurrentIndex(idx)
        if self._stack.currentWidget() is self._glossaries_tab:
            self._glossaries_tab.refresh()
        elif self._stack.currentWidget() is self._files_tab:
            self._files_tab.refresh()

    def _refresh_status(self) -> None:
        try:
            h = self._client.health()
        except BackendError:
            self._llm_badge.setText("● LLM: (offline)")
            self._llm_badge.setProperty("role", "muted")
            self._llm_badge.style().unpolish(self._llm_badge)
            self._llm_badge.style().polish(self._llm_badge)
            return
        nllb = h.get("nllb") or {}
        llm = h.get("llm") or {}
        if h.get("ok"):
            nllb_text = "NLLB ready" if nllb.get("available") else "NLLB unavailable"
            llm_text = "LLM ready" if llm.get("ready") else "LLM offline"
            self._llm_badge.setText(f"● {llm_text} · {nllb_text}")
            self.statusBar().showMessage("Backend connected.")
            try:
                state = self._client.get("/pipeline/state", timeout=2.0) or {}
                self._translate_tab.update_pipeline_state(state)
            except BackendError:
                pass
        else:
            self._llm_badge.setText("● LLM: ?")

    # ----- layout persistence -----

    def _restore_layout(self) -> None:
        geom = self._settings.value("MainWindow/geometry")
        if geom is not None:
            try:
                self.restoreGeometry(geom)
            except Exception:
                pass
        state = self._settings.value("MainWindow/state")
        if state is not None:
            try:
                self.restoreState(state)
            except Exception:
                pass
        page = self._settings.value("MainWindow/currentPage", 0, type=int)
        if 0 <= page < self._stack.count():
            self._sidebar.setCurrentRow(page)
            self._stack.setCurrentIndex(page)
        # Theme already restored by ThemeManager.restore_from.

    # ----- auto-update -----

    def _check_for_updates(self) -> None:
        """Background update check fired by QTimer.singleShot at boot.

        Never raises; on success it pops a non-modal :class:`UpdateDialog`
        and on no-update it stays silent. Skipped entirely in dev mode
        and when ``NOVELTRAD_SKIP_UPDATE=1``.
        """
        try:
            if is_skipped() or not self._updater.should_check():
                return
            info = self._updater.check()
        except Exception as exc:  # noqa: BLE001 - timer slot must not raise
            logger.warning("auto-update check failed: %s", exc)
            return
        if info is None:
            return
        self._present_update_dialog(info)

    def _on_manual_check_for_updates(self) -> None:
        """Slot for the ``Check for updates`` button in SettingsTab."""
        if is_skipped() or not self._updater.should_check():
            QMessageBox.information(
                self,
                "Updates",
                "Auto-update is disabled in this build (dev mode or "
                "NOVELTRAD_SKIP_UPDATE=1).",
            )
            return
        try:
            info = self._updater.check()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(
                self, "Update check failed", f"Could not contact GitHub: {exc}"
            )
            return
        if info is None:
            QMessageBox.information(
                self,
                "Up to date",
                f"You are running the latest stable version "
                f"({self._updater.current_version}).",
            )
            return
        self._present_update_dialog(info)

    def _present_update_dialog(self, info) -> None:  # noqa: ANN001 - UpdateInfo
        if (
            self._pending_update_dialog is not None
            and self._pending_update_dialog.isVisible()
        ):
            self._pending_update_dialog.raise_()
            self._pending_update_dialog.activateWindow()
            return
        dlg = UpdateDialog(self._updater, info, parent=self)
        self._pending_update_dialog = dlg
        dlg.finished.connect(lambda _r: self._on_update_dialog_closed())
        dlg.show()

    def _on_update_dialog_closed(self) -> None:
        self._pending_update_dialog = None

    def closeEvent(self, event: QCloseEvent) -> None:
        self._settings.setValue("MainWindow/geometry", self.saveGeometry())
        self._settings.setValue("MainWindow/state", self.saveState())
        self._settings.setValue(
            "MainWindow/currentPage", self._sidebar.currentRow()
        )
        self._theme.save_to(self._settings)
        try:
            self._debouncer.flush_now()
        except Exception:
            pass
        self._client.close()
        if self._backend_proc is not None and self._backend_proc.poll() is None:
            try:
                self._backend_proc.terminate()
            except Exception:
                pass
        super().closeEvent(event)


def QApplication_or_holder(widget: QWidget):  # noqa: ANN201
    from PyQt6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


__all__ = ["MainWindow", "SIDEBAR_ITEMS", "DRAWER_BREAKPOINT"]
