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
from src.gui.tabs.projects_tab import ProjectsTab
from src.gui.tabs.settings_tab import SettingsTab
from src.gui.tabs.translate_tab import TranslateTab as PipelineTab
from src.gui.theme import VALID_THEMES, ThemeManager
from src.gui.updater import Updater, is_skipped
from src.gui.widgets.activity_log import ActivityLogWidget
from src.gui.widgets.event_debouncer import EventDebouncer

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
            self._client.post(f"/projects/{pid}/activate", timeout=5.0)
        except BackendError as exc:
            self.statusBar().showMessage(
                self.tr("Could not activate project: {err}").format(err=exc), 4000
            )
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

    # ----- backend lifecycle -----

    def _start_backend(self) -> None:
        try:
            if self._client.health().get("ok"):
                self.statusBar().showMessage(self.tr("Backend connected."))
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
                self,
                self.tr("Backend"),
                self.tr("Could not start backend subprocess: {err}").format(err=exc),
            )
            return

        def _wait() -> None:
            if self._client.wait_ready(timeout_s=15.0):
                QTimer.singleShot(
                    0,
                    lambda: self.statusBar().showMessage(self.tr("Backend ready.")),
                )
            else:
                QTimer.singleShot(
                    0,
                    lambda: self.statusBar().showMessage(
                        self.tr("Backend did not respond.")
                    ),
                )

        import threading

        threading.Thread(target=_wait, daemon=True).start()

    def _restart_backend(self) -> None:
        """Kill the running backend subprocess and start a fresh one.

        Called when the user clicks "Save & Restart backend" in the
        Settings tab so the new LLM / NLLB env vars take effect without
        a full application restart.
        """
        if self._backend_proc is not None and self._backend_proc.poll() is None:
            try:
                self._backend_proc.terminate()
                self._backend_proc.wait(timeout=5)
            except Exception:
                try:
                    self._backend_proc.kill()
                    self._backend_proc.wait(timeout=3)
                except Exception:
                    pass
            self._backend_proc = None
        # Give the old process time to release the port.
        import time as _time
        _time.sleep(0.5)
        self._start_backend()

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
        self._pipeline_tab.on_pipeline_event(event)
        kind = event.get("type")
        if kind == "hltl_alert":
            self._show_hitl(event)
            self._notifier.notify(
                self.tr("HITL needed"),
                self.tr("Stage {stage}: {summary}").format(
                    stage=event.get("stage", "?"),
                    summary=(event.get("issue") or {}).get("summary", ""),
                ),
                level="warning",
            )
        elif kind == "agent_done":
            if self._files_tab is not None:
                self._files_tab.refresh()
        elif kind == "artifact_ready":
            self._pipeline_tab.on_artifact_ready(event.get("output_path", ""))
        elif kind == "pipeline_started":
            self.statusBar().showMessage(self.tr("Pipeline started."))
        elif kind == "hltl_unroutable":
            self.statusBar().showMessage(
                self.tr("HITL not routed: {reason}").format(
                    reason=event.get("reason", "?")
                ),
                5000,
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

    def _on_start_translation(self, payload: dict[str, Any]) -> str | None:
        try:
            body: dict[str, Any] = {
                "project_dir": payload.get("project_dir") or "./projects",
                "source_lang": payload.get("source_lang", "auto"),
                "target_lang": payload.get("target_lang", "fr"),
                "profile": payload.get("quality", "balanced"),
                "output_format": payload.get("output_format", "txt"),
                "parse": True,
            }
            # Prefer ``source_paths`` (list). Fall back to the legacy
            # single ``source_path`` field for back-compat with
            # re-opened projects that still carry the old payload.
            paths = payload.get("source_paths") or []
            if paths:
                body["source_paths"] = [str(p) for p in paths]
                body["source_path"] = str(paths[0])
            elif payload.get("source_path"):
                body["source_path"] = str(payload["source_path"])
            else:
                raise ValueError("payload has neither source_paths nor source_path")
            res = self._client.post("/projects", body=body, timeout=10.0)
        except BackendError as exc:
            self._pipeline_tab.on_project_start_failed(payload, str(exc))
            QMessageBox.warning(self, self.tr("Start failed"), str(exc))
            return None
        except Exception as exc:
            # Never let an unexpected error crash the Qt event loop.
            logger.exception("start translation: unexpected error")
            self._pipeline_tab.on_project_start_failed(payload, str(exc))
            QMessageBox.warning(
                self,
                self.tr("Start failed"),
                self.tr("Could not start translation: {err}").format(err=exc),
            )
            return None
        pid = res.get("project_id", "")
        self._pipeline_tab.on_project_created(payload, res)
        self._activity.on_event(
            {
                "type": "log",
                "message": self.tr("Project created: {pid}").format(pid=pid),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
        )
        self.statusBar().showMessage(
            self.tr("Project {pid} running…").format(pid=pid)
        )
        return pid

    def _on_replay_hltl(self) -> None:
        try:
            res = self._client.post("/orchestrator/hltl/replay", timeout=5.0) or {}
        except BackendError as exc:
            self.statusBar().showMessage(
                self.tr("Replay failed: {err}").format(err=exc), 4000
            )
            return
        routed = res.get("routed", 0)
        skipped = res.get("skipped", 0)
        self.statusBar().showMessage(
            self.tr("HITL replay: {routed} routed, {skipped} skipped").format(
                routed=routed, skipped=skipped
            ),
            4000,
        )

    def _on_retry(self, path: str) -> None:
        """Re-submit errored chunks for the project associated with *path*."""
        try:
            # 1. Fetch all chunks in error state.
            chunks_res = self._client.get(
                "/chunks", params={"status": "error", "limit": 500}, timeout=5.0
            ) or {}
            errored_ids = [c["id"] for c in chunks_res.get("items", []) if c.get("id")]
        except BackendError as exc:
            QMessageBox.warning(
                self,
                self.tr("Retry failed"),
                self.tr("Could not list errored chunks: {err}").format(err=exc),
            )
            return
        if not errored_ids:
            QMessageBox.information(
                self,
                self.tr("No error"),
                self.tr("No errored chunks found for this project."),
            )
            return
        try:
            res = self._client.post(
                "/pipeline/replay-chunks",
                body={"chunk_ids": errored_ids},
                timeout=10.0,
            ) or {}
        except BackendError as exc:
            QMessageBox.warning(
                self,
                self.tr("Retry failed"),
                self.tr("Could not retry chunks: {err}").format(err=exc),
            )
            return
        replayed = res.get("replayed", 0)
        self.statusBar().showMessage(
            self.tr("Retrying {n} errored chunk(s) for {path}…").format(
                n=replayed, path=Path(path).name
            ),
            5000,
        )
        self._activity.on_event(
            {
                "type": "log",
                "message": self.tr("Retry: {n} chunks re-injected for {path}").format(
                    n=replayed, path=path
                ),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
        )

    def _on_pause(self) -> None:
        try:
            self._client.post("/pipeline/pause", timeout=5.0)
            self.statusBar().showMessage(self.tr("Pipeline paused."), 3000)
        except BackendError as exc:
            QMessageBox.warning(self, self.tr("Pause failed"), str(exc))
        except Exception as exc:
            QMessageBox.warning(
                self, self.tr("Pause failed"), str(exc)
            )

    def _on_resume(self) -> None:
        try:
            self._client.post("/pipeline/resume", timeout=5.0)
            self.statusBar().showMessage(self.tr("Pipeline resumed."), 3000)
        except BackendError as exc:
            QMessageBox.warning(self, self.tr("Resume failed"), str(exc))
        except Exception as exc:
            QMessageBox.warning(
                self, self.tr("Resume failed"), str(exc)
            )

    def _on_stop(self) -> None:
        confirm = QMessageBox.question(
            self,
            self.tr("Stop pipeline"),
            self.tr(
                "Stop the current pipeline? Every queued file will be "
                "dropped and you can start a new batch after."
            ),
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            self._client.post("/pipeline/stop", timeout=10.0)
            self.statusBar().showMessage(self.tr("Pipeline stopped."), 3000)
        except BackendError as exc:
            QMessageBox.warning(self, self.tr("Stop failed"), str(exc))
        except Exception as exc:
            QMessageBox.warning(
                self, self.tr("Stop failed"), str(exc)
            )

    def _on_remove_queued_file(self, path: str) -> None:
        # Find the project_id for this path from the GUI cache.
        from PyQt6.QtWidgets import QMessageBox as _QMB
        item = self._pipeline_tab._queue_by_path.get(path)  # type: ignore[attr-defined]
        pid = (item or {}).get("project_id") or ""
        if not pid:
            return
        try:
            self._client.delete(
                f"/projects/{pid}/queue", timeout=5.0
            )
            self.statusBar().showMessage(
                self.tr("Removed {name} from the queue.").format(
                    name=(item or {}).get("name") or path
                ),
                3000,
            )
        except BackendError as exc:
            _QMB.warning(self, self.tr("Remove failed"), str(exc))
        except Exception as exc:
            _QMB.warning(self, self.tr("Remove failed"), str(exc))

    def _on_queue_completed(self, summary: dict[str, Any]) -> None:
        from PyQt6.QtMultimedia import QSoundEffect  # type: ignore
        from PyQt6.QtCore import QUrl

        done = int(summary.get("done", 0))
        failed = int(summary.get("failed", 0))
        total = int(summary.get("total", 0))
        # Play a short success sound. ``QSoundEffect`` resolves the
        # WAVE file at runtime; if the asset is missing we silently
        # skip the audio so the user still gets the visual popup.
        try:
            sound = QSoundEffect(self)
            from pathlib import Path as _P
            for cand in (
                _P(__file__).parent / "resources" / "sounds" / "success.wav",
                _P(__file__).parent / "src" / "gui" / "resources" / "sounds" / "success.wav",
            ):
                if cand.exists():
                    sound.setSource(QUrl.fromLocalFile(str(cand)))
                    sound.play()
                    break
        except Exception:
            pass
        # System bell as a fallback. The user can hear something even
        # if we did not ship a WAV asset.
        try:
            QApplication.beep()
        except Exception:
            pass
        if failed == 0:
            title = self.tr("Translation complete")
            text = self.tr(
                "All {total} file(s) translated successfully."
            ).format(total=total)
        else:
            title = self.tr("Translation finished with errors")
            text = self.tr(
                "{done}/{total} file(s) translated, {failed} failed."
            ).format(done=done, total=total, failed=failed)
        QMessageBox.information(self, title, text)
        self.statusBar().showMessage(title, 5000)

    def _on_assemble_requested(self, fmt: str) -> None:
        try:
            res = self._client.post(
                "/projects/assemble",
                body={"format": fmt},
                timeout=10.0,
            ) or {}
        except BackendError as exc:
            QMessageBox.warning(self, self.tr("Assemble failed"), str(exc))
            return
        if res.get("output_path"):
            self.statusBar().showMessage(
                self.tr("Output: {path}").format(path=res["output_path"]), 5000
            )

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

    def _refresh_status(self) -> None:
        try:
            h = self._client.health()
        except BackendError:
            self._set_badge(self.tr("● Offline"))
            self._was_offline = True
            return
        if not h.get("ok"):
            self._set_badge(self.tr("● LLM: ?"))
            self._was_offline = True
            return
        # Backend is online — refresh the current page if we just
        # recovered from an offline period (e.g. backend restart).
        if self._was_offline:
            self._was_offline = False
            current = self._stack.currentWidget()
            if current is self._projects_tab:
                self._projects_tab.refresh()
            elif current is self._glossary_tab:
                self._glossary_tab.refresh()
            elif current is self._files_tab:
                self._files_tab.refresh()
        self._set_badge(self._format_llm_badge(h))
        self._update_statusbar_usage(h)
        self._refresh_pipeline_state()

    def _set_badge(self, text: str) -> None:
        self._llm_badge.setText(text)
        self._llm_badge.setProperty("role", "muted")
        self._llm_badge.style().unpolish(self._llm_badge)
        self._llm_badge.style().polish(self._llm_badge)

    def _format_llm_badge(self, health: dict[str, Any]) -> str:
        llm = health.get("llm") or {}
        nllb = health.get("nllb") or {}
        mode_map = {
            "local": self.tr("● Local only"),
            "cloud": self.tr("● Cloud"),
            "hybrid": self.tr("● Hybrid"),
            "offline": self.tr("● LLM: offline"),
        }
        mode = llm.get("mode", "offline")
        badge = mode_map.get(mode, self.tr("● LLM: ?"))
        if nllb.get("available"):
            badge += f" · {self.tr('NLLB ready')}"
        return badge

    def _update_statusbar_usage(self, health: dict[str, Any]) -> None:
        llm = health.get("llm") or {}
        usage = llm.get("usage") or {}
        tokens = (usage.get("tokens_in") or 0) + (usage.get("tokens_out") or 0)
        if not tokens:
            self.statusBar().showMessage(self.tr("Backend connected."))
            return
        cost = usage.get("cost_usd") or 0.0
        tok_text = f"{tokens / 1000:.1f}k tok" if tokens >= 1000 else f"{tokens} tok"
        cost_text = f"${cost:.3f}" if cost > 0 else ""
        msg = f"{tok_text} · {cost_text}" if cost_text else tok_text
        self.statusBar().showMessage(msg)

    def _refresh_pipeline_state(self) -> None:
        try:
            state = self._client.get("/pipeline/state", timeout=2.0) or {}
            self._pipeline_tab.update_pipeline_state(state)
            # Enable the HITL replay button only when there are
            # chunks actually waiting for a human answer.
            pending = int(state.get("pending_hltl", 0) or 0)
            self._pipeline_tab._replay_btn.setEnabled(pending > 0)
        except BackendError:
            pass

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
                self.tr("Updates"),
                self.tr(
                    "Auto-update is disabled in this build (dev mode or "
                    "NOVELTRAD_SKIP_UPDATE=1)."
                ),
            )
            return
        try:
            info = self._updater.check()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(
                self,
                self.tr("Update check failed"),
                self.tr("Could not contact GitHub: {err}").format(err=exc),
            )
            return
        if info is None:
            QMessageBox.information(
                self,
                self.tr("Up to date"),
                self.tr(
                    "You are running the latest stable version "
                    "({version})."
                ).format(version=self._updater.current_version),
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
