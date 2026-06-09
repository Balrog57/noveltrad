"""MainWindow for NovelTrad v4 — TBL-inspired 4-tab GUI.

Lays out:

  [📚 NovelTrad]                              ● LLM: Ollama …   [🌙]
  ─────────────────────────────────────────────────────────────────
  [Translate*] [Settings] [Glossaries] [Files]
  ─────────────────────────────────────────────────────────────────
  … active tab content …
  ─────────────────────────────────────────────────────────────────
  Activity Log (collapsible, fed by WebSocket)

The window holds a single BackendClient that all tabs share. The
WebSocket fanout is wired to the activity log and to a HITL popup
that appears when a `hltl_alert` event arrives.
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

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.core.config_manager import ConfigManager
from src.gui.backend_client import BackendClient, BackendError
from src.gui.dialogs.chunk_detail_dialog import ChunkDetailDialog
from src.gui.dialogs.hitl_popup import HITLPopup
from src.gui.tabs.files_tab import FilesTab
from src.gui.tabs.glossaries_tab import GlossariesTab
from src.gui.tabs.settings_tab import SettingsTab
from src.gui.tabs.translate_tab import TranslateTab
from src.gui.widgets.activity_log import ActivityLogWidget

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NovelTrad")
        self.resize(1100, 760)

        self._config = ConfigManager()
        backend_url = os.environ.get("NOVELTRAD_BACKEND", "http://127.0.0.1:8765")
        self._client = BackendClient(backend_url)
        self._backend_proc: subprocess.Popen | None = None
        self._active_hitl: dict[str, HITLPopup] = {}

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # --- header (title + LLM badge) ---
        header = QWidget()
        header.setStyleSheet("QWidget { background: #0d0d0d; }")
        hbox = QHBoxLayout(header)
        hbox.setContentsMargins(12, 6, 12, 6)
        title = QLabel("📚  NovelTrad")
        title.setStyleSheet("font-size: 14pt; font-weight: 600;")
        hbox.addWidget(title)
        hbox.addStretch(1)
        self._llm_badge = QLabel("● LLM: …")
        self._llm_badge.setStyleSheet("color: #888;")
        hbox.addWidget(self._llm_badge)
        self._theme_btn = QPushButton("🌙")
        self._theme_btn.setFixedWidth(32)
        self._theme_btn.clicked.connect(self._toggle_theme)
        hbox.addWidget(self._theme_btn)
        root.addWidget(header)

        # --- tabs ---
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        self._translate_tab = TranslateTab(default_target=self._config.get("target_language", "fr"))
        self._translate_tab.startRequested.connect(self._on_start_translation)
        self._tabs.addTab(self._translate_tab, "Translate")
        self._settings_tab = SettingsTab()
        self._tabs.addTab(self._settings_tab, "Settings")
        self._glossaries_tab = GlossariesTab(self._client)
        self._tabs.addTab(self._glossaries_tab, "Glossaries")
        self._files_tab = FilesTab(self._client)
        self._files_tab.chunkActivated.connect(self._show_chunk_detail)
        self._tabs.addTab(self._files_tab, "Files")
        self._tabs.currentChanged.connect(self._on_tab_changed)
        root.addWidget(self._tabs, 1)

        # --- activity log ---
        self._activity = ActivityLogWidget()
        self._activity.chunkActivated.connect(self._show_chunk_detail)
        root.addWidget(self._activity)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Starting backend…")

        # Start backend subprocess (idempotent if already running).
        self._start_backend()
        # Periodically refresh LLM badge + status.
        self._timer = QTimer(self)
        self._timer.setInterval(2000)
        self._timer.timeout.connect(self._refresh_status)
        self._timer.start()
        QTimer.singleShot(500, self._post_startup)

    # ----- backend lifecycle -----

    def _start_backend(self) -> None:
        # If a backend is already responding, just connect.
        try:
            if self._client.health().get("ok"):
                self.statusBar().showMessage("Backend connected.")
                return
        except Exception:
            # Connection refused / timeout: we'll try to spawn one.
            pass
        try:
            env = os.environ.copy()
            env.setdefault("NOVELTRAD_HOST", "127.0.0.1")
            env.setdefault("NOVELTRAD_PORT", "8765")
            self._backend_proc = subprocess.Popen(  # noqa: S603
                [sys.executable, "-m", "src.backend.server", "--host", "127.0.0.1", "--port", "8765"],
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
        # Wait for readiness in background.
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
        # Open WebSocket and refresh state.
        try:
            self._client.open_websocket(self._on_ws_event)
        except Exception as exc:
            logger.warning("WebSocket open failed: %s", exc)
        self._refresh_status()

    def _on_ws_event(self, event: dict[str, Any]) -> None:
        # Marshal back to the GUI thread via QTimer.singleShot(0, …)
        QTimer.singleShot(0, lambda: self._handle_event(event))

    def _handle_event(self, event: dict[str, Any]) -> None:
        self._activity.on_event(event)
        kind = event.get("type")
        if kind == "hltl_alert":
            self._show_hitl(event)
        elif kind in ("agent_done", "chunks_submitted", "assemble_triggered"):
            # Cheap re-poll of the Files tab.
            if self._tabs.currentIndex() == 3:
                self._files_tab.refresh()
        elif kind == "pipeline_started":
            self.statusBar().showMessage("Pipeline started.")

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

    def _on_tab_changed(self, _idx: int) -> None:
        if self._tabs.currentWidget() is self._glossaries_tab:
            self._glossaries_tab.refresh()
        elif self._tabs.currentWidget() is self._files_tab:
            self._files_tab.refresh()

    def _refresh_status(self) -> None:
        try:
            h = self._client.health()
        except BackendError:
            self._llm_badge.setText("● LLM: (offline)")
            self._llm_badge.setStyleSheet("color: #ff6b6b;")
            return
        if h.get("ok"):
            self._llm_badge.setText("● LLM: ready")
            self._llm_badge.setStyleSheet("color: #7be395;")
        else:
            self._llm_badge.setText("● LLM: ?")
            self._llm_badge.setStyleSheet("color: #ffd166;")

    def _toggle_theme(self) -> None:
        cur = self._config.get("ui", {}) or {}
        cur = dict(cur) if isinstance(cur, dict) else {}
        cur["dark"] = not bool(cur.get("dark", True))
        cfg = self._config.config
        cfg["ui"] = cur
        self._config.save_config()
        QMessageBox.information(
            self,
            "Theme",
            "Theme change will apply on next launch.",
        )

    # ----- shutdown -----

    def closeEvent(self, event: QCloseEvent) -> None:
        self._client.close()
        if self._backend_proc is not None and self._backend_proc.poll() is None:
            try:
                self._backend_proc.terminate()
            except Exception:
                pass
        super().closeEvent(event)


__all__ = ["MainWindow"]
