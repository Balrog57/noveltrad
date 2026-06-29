"""MainWindow for NovelTrad v4 — sidebar + stacked pages layout.

Layout:

   [📚 NovelTrad]              ● LLM: Ollama …   [🌙] [☰]
   ────────────────────────────────────────────────────────
   [ Translate  ] ┌────────────────────────────────────┐
   [ Projects  ]  │   page content                       │
   [ Glossaries]  │   (QStackedWidget)                   │
   [ Files     ]  │                                      │
   [ Settings  ]  │                                      │
   ───────────────┴──────────────────────────────────────┘
   Activity Log (collapsible, fed by WebSocket)

Responsive: below 900 px the sidebar collapses into a drawer
toggled by the hamburger button in the header. State is persisted
via QSettings on ``closeEvent`` and restored on ``__init__``.

Module layout
-------------
After the v4 split this module holds only the layout, the signal
wiring, the navigation, and the methods the test suite pokes at
directly (``_apply_responsive_mode``, ``_toggle_drawer``,
``_activate_project_locally``). The focused responsibilities live
in :mod:`.main_window_collaborators` as five small classes:

  * ``backend``  -- start / restart / post-startup.
  * ``events``   -- WebSocket event routing, HITL popups, chunk detail.
  * ``actions``  -- the ``_on_*`` slots wired to the pipeline tab.
  * ``status``   -- the 2s health poll: badge, statusbar, pipeline state.
  * ``updates``  -- background + manual update checks and the dialog.

The main window keeps one of each and exposes thin delegates for the
private API the test suite uses.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from PyQt6.QtCore import QSettings, Qt, QTimer
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
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
from src.gui.notifier import Notifier
from src.gui.tabs.files_tab import FilesTab
from src.gui.tabs.glossaries_tab import GlossariesTab
from src.gui.tabs.projects_tab import ProjectsTab
from src.gui.tabs.settings_tab import SettingsTab
from src.gui.tabs.translate_tab import TranslateTab as PipelineTab
from src.gui.theme import ThemeManager
from src.gui.updater import Updater
from src.gui.widgets.activity_log import ActivityLogWidget
from src.gui.widgets.event_debouncer import EventDebouncer

from .main_window_collaborators import (
    BackendLifecycle,
    EventRouter,
    PipelineActions,
    StatusRefresh,
    UpdateChecker,
)

logger = logging.getLogger(__name__)


SIDEBAR_ITEMS: tuple[tuple[str, str], ...] = (
    ("projects", "Projects"),
    ("pipeline", "Pipeline"),
    ("glossary", "Glossary"),
    ("files", "Files"),
    ("settings", "Settings"),
)

DRAWER_BREAKPOINT = 700


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("NovelTrad"))
        self.resize(1100, 760)

        self._config = ConfigManager()
        self._config.apply_environment()
        self._was_offline = True  # track health transitions for auto-refresh
        backend_url = os.environ.get("NOVELTRAD_BACKEND", "http://127.0.0.1:8765")
        self._client = BackendClient(backend_url)
        import subprocess

        self._backend_proc: subprocess.Popen | None = None  # type: ignore[name-defined]
        self._active_hitl: dict[str, Any] = {}
        self._closing = False
        self._notifier = Notifier(self)
        # Auto-updater. We never auto-update when the env var disables
        # it or when we're running from the dev checkout (Updater
        # short-circuits in that case).
        import src as _src_pkg

        self._updater = Updater(current_version=_src_pkg.__version__)
        self._pending_update_dialog: Any = None

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
        configure(
            self._hamburger,
            name="Toggle sidebar drawer",
            tooltip=self.tr("Toggle sidebar"),
        )
        hbox.addWidget(self._hamburger)

        title = QLabel(self.tr("📚  NovelTrad"))
        title.setProperty("role", "title")
        hbox.addWidget(title)
        hbox.addStretch(1)
        self._llm_badge = QLabel(self.tr("● LLM: …"))
        self._llm_badge.setProperty("role", "muted")
        hbox.addWidget(self._llm_badge)
        self._theme_btn = QPushButton("🌙")
        self._theme_btn.setFixedWidth(36)
        self._theme_btn.clicked.connect(self._cycle_theme)
        configure(
            self._theme_btn,
            name=self.tr("Cycle theme"),
            tooltip=self.tr("Switch theme (Ctrl+Shift+T)"),
        )
        hbox.addWidget(self._theme_btn)
        root.addWidget(header)

        # --- sidebar + stacked pages in a splitter ---
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._sidebar = QListWidget()
        self._sidebar_items: list[QListWidgetItem] = []
        for i, (_key, label) in enumerate(SIDEBAR_ITEMS):
            item = QListWidgetItem(self.tr(label))
            self._sidebar.addItem(item)
            self._sidebar_items.append(item)
            # Disable project-dependent tabs until a project is activated.
            if _key in ("pipeline", "glossary", "files"):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
        self._sidebar.setFixedWidth(200)
        self._sidebar.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        configure(self._sidebar, name="Navigation")
        self._sidebar.currentRowChanged.connect(self._on_sidebar_changed)

        self._stack = QStackedWidget()
        self._projects_tab = ProjectsTab(self._client)
        self._projects_tab.projectActivated.connect(self._on_project_activated)
        self._stack.addWidget(self._projects_tab)
        self._pipeline_tab = PipelineTab(
            default_target="fr", client=self._client
        )
        self._pipeline_tab.startRequested.connect(self._on_start_translation)
        self._pipeline_tab.replayHltlRequested.connect(self._on_replay_hltl)
        self._pipeline_tab.assembleRequested.connect(self._on_assemble_requested)
        self._pipeline_tab.outputFolderRequested.connect(self._on_open_output_folder)
        self._pipeline_tab.retryRequested.connect(self._on_retry)
        self._pipeline_tab.pauseRequested.connect(self._on_pause)
        self._pipeline_tab.resumeRequested.connect(self._on_resume)
        self._pipeline_tab.stopRequested.connect(self._on_stop)
        self._pipeline_tab.fileRemoved.connect(self._on_remove_queued_file)
        self._pipeline_tab.queueCompleted.connect(self._on_queue_completed)
        self._stack.addWidget(self._pipeline_tab)
        self._glossary_tab = GlossariesTab(self._client)
        self._stack.addWidget(self._glossary_tab)
        self._files_tab = FilesTab(self._client)
        self._files_tab.chunkActivated.connect(self._show_chunk_detail)
        self._stack.addWidget(self._files_tab)
        self._settings_tab = SettingsTab()
        self._settings_tab.checkForUpdatesRequested.connect(
            self._on_manual_check_for_updates
        )
        self._settings_tab.restartBackendRequested.connect(
            self._restart_backend
        )
        self._stack.addWidget(self._settings_tab)

        self._splitter.addWidget(self._sidebar)
        self._splitter.addWidget(self._stack)
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setCollapsible(0, True)
        self._splitter.setHandleWidth(1)
        root.addWidget(self._splitter, 1)

        # --- activity log ---
        self._activity = ActivityLogWidget()
        self._activity.chunkActivated.connect(self._show_chunk_detail)
        root.addWidget(self._activity)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage(self.tr("Starting backend…"))

        # WebSocket event debouncer.
        self._debouncer = EventDebouncer(self._on_event_batch, parent=self)

        # Collaborators: each owns a focused responsibility and reads
        # shared state through this main window.
        self.backend = BackendLifecycle(self)
        self.events = EventRouter(self)
        self.actions = PipelineActions(self)
        self.status = StatusRefresh(self)
        self.updates = UpdateChecker(self)

        # Install global shortcuts.
        self._install_shortcuts()

        # Start backend subprocess (idempotent if already running).
        self.backend.start()
        # Periodically refresh LLM badge + status.
        self._timer = QTimer(self)
        self._timer.setInterval(2000)
        self._timer.timeout.connect(self._refresh_status)
        self._timer.start()
        QTimer.singleShot(500, self.backend.post_startup)
        # Restore layout.
        self._restore_layout()
        # Apply initial responsive mode once the window is actually
        # shown (resizeEvent won't fire on a hidden widget). Only seed
        # the splitter sizes when the user has no saved layout; otherwise
        # _restore_layout() above will set the proper sizes from QSettings
        # and we must not clobber them.
        saved_state = self._settings.value("MainWindow/state")
        if not saved_state:
            self._drawer_open = True
            self._sidebar.setVisible(True)
            self._splitter.setSizes([200, max(400, self.width() - 200)])
        else:
            self._drawer_open = self.width() >= DRAWER_BREAKPOINT

        # Background auto-update check, fires once the UI is settled.
        QTimer.singleShot(3000, self._check_for_updates)

    # ----- responsive -----

    def resizeEvent(self, event) -> None:  # noqa: ANN001 - Qt signature
        super().resizeEvent(event)
        self._apply_responsive_mode(event.size().width())

    def _apply_responsive_mode(self, width: int) -> None:
        drawer = width < DRAWER_BREAKPOINT
        if drawer:
            if self._drawer_open:
                self._sidebar.setVisible(False)
                self._drawer_open = False
                self._splitter.setSizes([0, width])
        else:
            if not self._drawer_open:
                self._sidebar.setVisible(True)
                self._drawer_open = True
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
        if hasattr(self._pipeline_tab, "_cloud"):
            self._pipeline_tab._cloud._open_dialog()  # type: ignore[attr-defined]

    def _action_rerun(self) -> None:
        if self._stack.currentWidget() is self._projects_tab:
            row = self._projects_tab._table.currentRow()
            if 0 <= row < len(self._projects_tab._projects):
                self._on_project_activated(self._projects_tab._projects[row])
                return
        self._on_replay_hltl()

    def _on_project_activated(self, proj: dict[str, Any]) -> None:
        """Activate a project — set it as active on the backend and
        refresh all dependent tabs (Pipeline, Files, Glossary)."""
        pid = proj.get("project_id", "")
        if not pid:
            return
        self._sidebar.setCurrentRow(0)  # stay on Projects
        try:
            # Tell the backend this is the active project.
            data = self._client.post(f"/projects/{pid}/activate", timeout=5.0) or {}
        except BackendError as exc:
            self.statusBar().showMessage(
                self.tr("Could not activate project: {err}").format(err=exc), 4000
            )
            return
        canonical = data.get("project") if isinstance(data.get("project"), dict) else proj
        self._activate_project_locally(canonical)
        self._projects_tab.refresh()

    def _activate_project_locally(self, proj: dict[str, Any]) -> None:
        pid = proj.get("project_id", "")
        if not pid:
            return
        # Enable project-dependent sidebar items.
        for i, (_key, _label) in enumerate(SIDEBAR_ITEMS):
            if _key in ("pipeline", "glossary", "files"):
                self._sidebar_items[i].setFlags(
                    self._sidebar_items[i].flags() | Qt.ItemFlag.ItemIsEnabled
                )
        # Refresh all project-scoped tabs.
        self._pipeline_tab.set_project(proj)
        if hasattr(self._files_tab, "set_project"):
            self._files_tab.set_project(proj)
        if hasattr(self._glossary_tab, "set_project"):
            self._glossary_tab.set_project(proj)
        self.statusBar().showMessage(
            self.tr("Project: {name}").format(
                name=proj.get("name", pid[:8])
            ),
            4000,
        )

    def _action_settings(self) -> None:
        idx = next(
            (i for i, (k, _) in enumerate(SIDEBAR_ITEMS) if k == "settings"), 0
        )
        self._sidebar.setCurrentRow(idx)
        self._stack.setCurrentIndex(idx)

    def _action_help(self) -> None:
        lines = [self.tr("Keyboard shortcuts:")]
        for spec in GLOBAL_SHORTCUTS:
            lines.append(f"  {spec.sequence:<14} {spec.label}")
        QMessageBox.information(self, self.tr("Help"), "\n".join(lines))

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
        self.statusBar().showMessage(self.tr("Theme: {name}").format(name=new_name), 2000)

    # ----- projects placeholder -----

    def _build_projects_placeholder(self) -> QWidget:
        page = QFrame()
        page.setProperty("role", "card")
        v = QVBoxLayout(page)
        v.setContentsMargins(24, 24, 24, 24)
        title = QLabel(self.tr("Recent projects"))
        title.setProperty("role", "title")
        v.addWidget(title)
        hint = QLabel(
            self.tr(
                "Projects will appear here as you translate. "
                "Each entry shows source, target, date and a quick re-open action."
            )
        )
        hint.setProperty("role", "muted")
        hint.setWordWrap(True)
        v.addWidget(hint)
        v.addStretch(1)
        configure(
            page,
            name=self.tr("Recent projects"),
            description=self.tr("List of past translation runs."),
        )
        return page

    # ----- navigation -----

    def _on_sidebar_changed(self, idx: int) -> None:
        if idx < 0 or idx >= self._stack.count():
            return
        # Block navigation to disabled (project-dependent) tabs.
        item = self._sidebar.item(idx)
        if item and not (item.flags() & Qt.ItemFlag.ItemIsEnabled):
            self._sidebar.setCurrentRow(0)  # force back to Projects
            return
        self._stack.setCurrentIndex(idx)
        if self._stack.currentWidget() is self._glossary_tab:
            self._glossary_tab.refresh()
        elif self._stack.currentWidget() is self._files_tab:
            self._files_tab.refresh()
        elif self._stack.currentWidget() is self._projects_tab:
            self._projects_tab.refresh()

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
            previous = self._sidebar.blockSignals(True)
            try:
                self._sidebar.setCurrentRow(page)
                self._stack.setCurrentIndex(page)
            finally:
                self._sidebar.blockSignals(previous)
        # Theme already restored by ThemeManager.restore_from.

    def closeEvent(self, event: QCloseEvent) -> None:
        self._closing = True
        if hasattr(self, "_timer"):
            self._timer.stop()
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

    # ------------------------------------------------------------------
    # backward-compatible thin delegates (signal wiring + the test
    # suite's private API). Each method is a one-line forward to the
    # matching collaborator.
    # ------------------------------------------------------------------

    # --- BackendLifecycle ---
    def _start_backend(self) -> None:
        self.backend.start()

    def _restart_backend(self) -> None:
        self.backend.restart()

    def _post_startup(self) -> None:
        self.backend.post_startup()

    def _restore_active_project_context(self) -> None:
        self.backend.restore_active_project_context()

    # --- EventRouter ---
    def _on_ws_event(self, event: dict[str, Any]) -> None:
        self.events.on_ws_event(event)

    def _on_event_batch(self, batch: list[dict[str, Any]]) -> None:
        self.events.on_event_batch(batch)

    def _handle_event(self, event: dict[str, Any]) -> None:
        self.events.handle_event(event)

    def _show_hitl(self, event: dict[str, Any]) -> None:
        self.events.show_hitl(event)

    def _show_chunk_detail(self, chunk_id: str) -> None:
        self.events.show_chunk_detail(chunk_id)

    # --- PipelineActions ---
    def _on_start_translation(self, payload: dict[str, Any]) -> str | None:
        return self.actions.on_start_translation(payload)

    def _on_replay_hltl(self) -> None:
        self.actions.on_replay_hltl()

    def _on_retry(self, path: str) -> None:
        self.actions.on_retry(path)

    def _on_pause(self) -> None:
        self.actions.on_pause()

    def _on_resume(self) -> None:
        self.actions.on_resume()

    def _on_stop(self) -> None:
        self.actions.on_stop()

    def _on_remove_queued_file(self, path: str) -> None:
        self.actions.on_remove_queued_file(path)

    def _on_queue_completed(self, summary: dict[str, Any]) -> None:
        self.actions.on_queue_completed(summary)

    def _on_assemble_requested(self, fmt: str) -> None:
        self.actions.on_assemble_requested(fmt)

    def _on_open_output_folder(self, output_path: str) -> None:
        self.actions.on_open_output_folder(output_path)

    # --- StatusRefresh ---
    def _refresh_status(self) -> None:
        self.status.refresh()

    def _set_badge(self, text: str) -> None:
        self.status.set_badge(text)

    def _format_llm_badge(self, health: dict[str, Any]) -> str:
        return self.status.format_llm_badge(health)

    def _update_statusbar_usage(self, health: dict[str, Any]) -> None:
        self.status.update_statusbar_usage(health)

    def _refresh_pipeline_state(self) -> None:
        self.status.refresh_pipeline_state()

    # --- UpdateChecker ---
    def _check_for_updates(self) -> None:
        self.updates.check()

    def _on_manual_check_for_updates(self) -> None:
        self.updates.on_manual_check()

    def _present_update_dialog(self, info) -> None:  # noqa: ANN001
        self.updates.present_update_dialog(info)

    def _on_update_dialog_closed(self) -> None:
        self.updates.on_update_dialog_closed()


def QApplication_or_holder(widget: QWidget):  # noqa: ANN201
    from PyQt6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


__all__ = ["MainWindow", "SIDEBAR_ITEMS", "DRAWER_BREAKPOINT"]