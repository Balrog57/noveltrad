"""Internal collaborators for ``MainWindow``.

The Qt main window used to be a 1060-line god class with 45 methods on
one ``QMainWindow`` subclass. After the v4 split the focused
responsibilities live here as small classes; ``MainWindow`` keeps the
layout, the signal wiring, and the methods the test suite pokes at
directly (``_apply_responsive_mode``, ``_toggle_drawer``,
``_activate_project_locally``).

Each collaborator takes the main window in its constructor. The
collaborator accesses shared state (``_client``, ``_pipeline_tab``,
``_activity``, ``statusBar()``, ``tr()``, ...) through that reference.
This is a deliberate two-way link: it is internal and the alternative
(passing 10 things to each constructor) would be noisier without any
real decoupling benefit.

What stays on ``MainWindow`` (see ``main_window.py``):
  * Layout: ``__init__``, ``resizeEvent``, ``_apply_responsive_mode``,
    ``_toggle_drawer``, ``_build_projects_placeholder``, ``_restore_layout``,
    ``closeEvent``.
  * Navigation: ``_on_sidebar_changed``, ``_action_settings``,
    ``_action_help``, ``_action_close_overlay``, ``_action_open_file``,
    ``_action_rerun``.
  * Project activation: ``_on_project_activated``,
    ``_activate_project_locally`` (the test suite calls this unbound
    with a ``FakeWindow``, so it must stay a real method).
  * Shortcuts: ``_install_shortcuts``.
  * Theme: ``_cycle_theme``.

What moves here:
  * ``BackendLifecycle`` -- start / restart / post-startup / restore
    active project context.
  * ``EventRouter``     -- WebSocket event routing, HITL popups, chunk
    detail dialog.
  * ``PipelineActions`` -- the ``_on_*`` slots wired to the pipeline
    tab's signals (start / replay / retry / pause / resume / stop /
    remove / queue-completed / assemble / open-output).
  * ``StatusRefresh``   -- the 2s health poll: badge, statusbar usage,
    pipeline state refresh.
  * ``UpdateChecker``   -- background + manual update checks and the
    update dialog.
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QTimer, QUrl
from PyQt6.QtWidgets import QApplication, QMessageBox

from src.gui.backend_client import BackendError
from src.gui.dialogs.chunk_detail_dialog import ChunkDetailDialog
from src.gui.dialogs.hitl_popup import HITLPopup
from src.gui.dialogs.update_dialog import UpdateDialog
from src.gui.updater import is_skipped

if TYPE_CHECKING:
    from .main_window import MainWindow

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# BackendLifecycle
# ---------------------------------------------------------------------------


class BackendLifecycle:
    """Start / restart the backend subprocess and re-open the WebSocket.

    The main window owns the ``BackendClient``; this collaborator drives
    its lifecycle: it probes for an already-running backend, spawns a
    subprocess if none is found, waits for it to become ready, and
    re-opens the WebSocket + restores the active project context after
    a (re)start.
    """

    def __init__(self, win: "MainWindow"):
        self._win = win

    def start(self) -> None:
        try:
            if self._win._client.health().get("ok"):
                self._win.statusBar().showMessage(self._win.tr("Backend connected."))
                return
        except Exception:
            pass
        try:
            env = os.environ.copy()
            self._win._config.apply_environment()
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
            self._win._backend_proc = subprocess.Popen(  # noqa: S603
                backend_cmd,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=str(Path(__file__).resolve().parents[2]),
            )
        except Exception as exc:
            QMessageBox.warning(
                self._win,
                self._win.tr("Backend"),
                self._win.tr("Could not start backend subprocess: {err}").format(err=exc),
            )
            return

        def _wait() -> None:
            if self._win._client.wait_ready(timeout_s=15.0):
                QTimer.singleShot(
                    0,
                    lambda: self._win.statusBar().showMessage(self._win.tr("Backend ready.")),
                )
            else:
                QTimer.singleShot(
                    0,
                    lambda: self._win.statusBar().showMessage(
                        self._win.tr("Backend did not respond.")
                    ),
                )

        import threading

        threading.Thread(target=_wait, daemon=True).start()

    def restart(self) -> None:
        """Kill the running backend subprocess and start a fresh one.

        Called when the user clicks "Save & Restart backend" in the
        Settings tab so the new LLM / NLLB env vars take effect without
        a full application restart.
        """
        if (
            self._win._backend_proc is not None
            and self._win._backend_proc.poll() is None
        ):
            try:
                self._win._backend_proc.terminate()
                self._win._backend_proc.wait(timeout=5)
            except Exception:
                try:
                    self._win._backend_proc.kill()
                    self._win._backend_proc.wait(timeout=3)
                except Exception:
                    pass
            self._win._backend_proc = None
        # Give the old process time to release the port.
        time.sleep(0.5)
        self.start()

    def post_startup(self) -> None:
        if self._win._closing:
            return
        try:
            self._win._client.open_websocket(self._win.events.on_ws_event)
        except Exception as exc:
            logger.warning("WebSocket open failed: %s", exc)
        self.restore_active_project_context()
        self._win.status.refresh()

    def restore_active_project_context(self) -> None:
        try:
            data = self._win._client.get("/projects/active", timeout=3.0) or {}
        except BackendError:
            return
        project = data.get("project")
        if isinstance(project, dict) and project.get("project_id"):
            self._win._activate_project_locally(project)
            if self._win._stack.currentWidget() is self._win._projects_tab:
                self._win._projects_tab.refresh()


# ---------------------------------------------------------------------------
# EventRouter
# ---------------------------------------------------------------------------


class EventRouter:
    """Routes WebSocket events to the right UI widget.

    The debouncer hands us a batch; we walk it and dispatch each event
    to the activity log, the pipeline tab, and any popup (HITL, chunk
    detail) that the event type demands.
    """

    def __init__(self, win: "MainWindow"):
        self._win = win

    def on_ws_event(self, event: dict[str, Any]) -> None:
        # Marshal to GUI thread and into the debouncer.
        self._win._debouncer.push(event)

    def on_event_batch(self, batch: list[dict[str, Any]]) -> None:
        for event in batch:
            self.handle_event(event)

    def handle_event(self, event: dict[str, Any]) -> None:
        self._win._activity.on_event(event)
        self._win._pipeline_tab.on_pipeline_event(event)
        kind = event.get("type")
        if kind == "hltl_alert":
            self.show_hitl(event)
            self._win._notifier.notify(
                self._win.tr("HITL needed"),
                self._win.tr("Stage {stage}: {summary}").format(
                    stage=event.get("stage", "?"),
                    summary=(event.get("issue") or {}).get("summary", ""),
                ),
                level="warning",
            )
        elif kind == "agent_done":
            if self._win._files_tab is not None:
                self._win._files_tab.refresh()
        elif kind == "artifact_ready":
            self._win._pipeline_tab.on_artifact_ready(event.get("output_path", ""))
        elif kind == "pipeline_started":
            self._win.statusBar().showMessage(self._win.tr("Pipeline started."))
        elif kind == "hltl_unroutable":
            self._win.statusBar().showMessage(
                self._win.tr("HITL not routed: {reason}").format(
                    reason=event.get("reason", "?")
                ),
                5000,
            )

    def show_hitl(self, event: dict[str, Any]) -> None:
        rid = event.get("request_id", "")
        if not rid or rid in self._win._active_hitl:
            return
        dlg = HITLPopup(
            request_id=rid,
            chunk_id=event.get("chunk_id", ""),
            stage=event.get("stage", ""),
            issue=event.get("issue") or {},
            client=self._win._client,
            parent=self._win,
        )
        self._win._active_hitl[rid] = dlg
        dlg.finished.connect(lambda _r, k=rid: self._win._active_hitl.pop(k, None))
        dlg.show()

    def show_chunk_detail(self, chunk_id: str) -> None:
        if not chunk_id:
            return
        dlg = ChunkDetailDialog(chunk_id, self._win._client, parent=self._win)
        dlg.exec()


# ---------------------------------------------------------------------------
# PipelineActions
# ---------------------------------------------------------------------------


class PipelineActions:
    """Slots wired to the pipeline tab's signals.

    Each method is the receiver for one signal emitted by
    ``TranslateTab``: ``startRequested``, ``replayHltlRequested``,
    ``assembleRequested``, ``outputFolderRequested``, ``retryRequested``,
    ``pauseRequested``, ``resumeRequested``, ``stopRequested``,
    ``fileRemoved``, ``queueCompleted``. They all hit the backend via
    ``self._win._client`` and surface success / failure through the
    status bar or a ``QMessageBox``.
    """

    def __init__(self, win: "MainWindow"):
        self._win = win

    def on_start_translation(self, payload: dict[str, Any]) -> str | None:
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
            res = self._win._client.post("/projects", body=body, timeout=10.0)
        except BackendError as exc:
            self._win._pipeline_tab.on_project_start_failed(payload, str(exc))
            QMessageBox.warning(self._win, self._win.tr("Start failed"), str(exc))
            return None
        except Exception as exc:
            # Never let an unexpected error crash the Qt event loop.
            logger.exception("start translation: unexpected error")
            self._win._pipeline_tab.on_project_start_failed(payload, str(exc))
            QMessageBox.warning(
                self._win,
                self._win.tr("Start failed"),
                self._win.tr("Could not start translation: {err}").format(err=exc),
            )
            return None
        pid = res.get("project_id", "")
        self._win._pipeline_tab.on_project_created(payload, res)
        self._win._activity.on_event(
            {
                "type": "log",
                "message": self._win.tr("Project created: {pid}").format(pid=pid),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
        )
        self._win.statusBar().showMessage(
            self._win.tr("Project {pid} running…").format(pid=pid)
        )
        return pid

    def on_replay_hltl(self) -> None:
        try:
            res = self._win._client.post("/orchestrator/hltl/replay", timeout=5.0) or {}
        except BackendError as exc:
            self._win.statusBar().showMessage(
                self._win.tr("Replay failed: {err}").format(err=exc), 4000
            )
            return
        routed = res.get("routed", 0)
        skipped = res.get("skipped", 0)
        self._win.statusBar().showMessage(
            self._win.tr("HITL replay: {routed} routed, {skipped} skipped").format(
                routed=routed, skipped=skipped
            ),
            4000,
        )

    def on_retry(self, path: str) -> None:
        """Re-submit errored chunks for the project associated with *path*."""
        try:
            chunks_res = self._win._client.get(
                "/chunks", params={"status": "error", "limit": 500}, timeout=5.0
            ) or {}
            errored_ids = [
                c["id"] for c in chunks_res.get("items", []) if c.get("id")
            ]
        except BackendError as exc:
            QMessageBox.warning(
                self._win,
                self._win.tr("Retry failed"),
                self._win.tr("Could not list errored chunks: {err}").format(err=exc),
            )
            return
        if not errored_ids:
            QMessageBox.information(
                self._win,
                self._win.tr("No error"),
                self._win.tr("No errored chunks found for this project."),
            )
            return
        try:
            res = self._win._client.post(
                "/pipeline/replay-chunks",
                body={"chunk_ids": errored_ids},
                timeout=10.0,
            ) or {}
        except BackendError as exc:
            QMessageBox.warning(
                self._win,
                self._win.tr("Retry failed"),
                self._win.tr("Could not retry chunks: {err}").format(err=exc),
            )
            return
        replayed = res.get("replayed", 0)
        self._win.statusBar().showMessage(
            self._win.tr("Retrying {n} errored chunk(s) for {path}…").format(
                n=replayed, path=Path(path).name
            ),
            5000,
        )
        self._win._activity.on_event(
            {
                "type": "log",
                "message": self._win.tr(
                    "Retry: {n} chunks re-injected for {path}"
                ).format(n=replayed, path=path),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
        )

    def on_pause(self) -> None:
        try:
            self._win._client.post("/pipeline/pause", timeout=5.0)
            self._win.statusBar().showMessage(self._win.tr("Pipeline paused."), 3000)
        except BackendError as exc:
            QMessageBox.warning(self._win, self._win.tr("Pause failed"), str(exc))
        except Exception as exc:
            QMessageBox.warning(self._win, self._win.tr("Pause failed"), str(exc))

    def on_resume(self) -> None:
        try:
            self._win._client.post("/pipeline/resume", timeout=5.0)
            self._win.statusBar().showMessage(self._win.tr("Pipeline resumed."), 3000)
        except BackendError as exc:
            QMessageBox.warning(self._win, self._win.tr("Resume failed"), str(exc))
        except Exception as exc:
            QMessageBox.warning(self._win, self._win.tr("Resume failed"), str(exc))

    def on_stop(self) -> None:
        confirm = QMessageBox.question(
            self._win,
            self._win.tr("Stop pipeline"),
            self._win.tr(
                "Stop the current pipeline? Every queued file will be "
                "dropped and you can start a new batch after."
            ),
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            self._win._client.post("/pipeline/stop", timeout=10.0)
            self._win.statusBar().showMessage(self._win.tr("Pipeline stopped."), 3000)
        except BackendError as exc:
            QMessageBox.warning(self._win, self._win.tr("Stop failed"), str(exc))
        except Exception as exc:
            QMessageBox.warning(self._win, self._win.tr("Stop failed"), str(exc))

    def on_remove_queued_file(self, path: str) -> None:
        from PyQt6.QtWidgets import QMessageBox as _QMB

        item = self._win._pipeline_tab._queue_by_path.get(path)  # type: ignore[attr-defined]
        pid = (item or {}).get("project_id") or ""
        if not pid:
            return
        try:
            self._win._client.delete(f"/projects/{pid}/queue", timeout=5.0)
            self._win.statusBar().showMessage(
                self._win.tr("Removed {name} from the queue.").format(
                    name=(item or {}).get("name") or path
                ),
                3000,
            )
        except BackendError as exc:
            _QMB.warning(self._win, self._win.tr("Remove failed"), str(exc))
        except Exception as exc:
            _QMB.warning(self._win, self._win.tr("Remove failed"), str(exc))

    def on_queue_completed(self, summary: dict[str, Any]) -> None:
        from PyQt6.QtMultimedia import QSoundEffect  # type: ignore

        done = int(summary.get("done", 0))
        failed = int(summary.get("failed", 0))
        total = int(summary.get("total", 0))
        # Play a short success sound. ``QSoundEffect`` resolves the
        # WAVE file at runtime; if the asset is missing we silently
        # skip the audio so the user still gets the visual popup.
        try:
            sound = QSoundEffect(self._win)
            for cand in (
                Path(__file__).parent / "resources" / "sounds" / "success.wav",
                Path(__file__).parent
                / "src"
                / "gui"
                / "resources"
                / "sounds"
                / "success.wav",
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
            title = self._win.tr("Translation complete")
            text = self._win.tr(
                "All {total} file(s) translated successfully."
            ).format(total=total)
        else:
            title = self._win.tr("Translation finished with errors")
            text = self._win.tr(
                "{done}/{total} file(s) translated, {failed} failed."
            ).format(done=done, total=total, failed=failed)
        QMessageBox.information(self._win, title, text)
        self._win.statusBar().showMessage(title, 5000)

    def on_assemble_requested(self, fmt: str) -> None:
        """Force-assemble: call the backend with the correct output path."""
        try:
            project_dir = (
                self._win._pipeline_tab._project_dir
                if hasattr(self._win._pipeline_tab, "_project_dir")
                else ""
            )
            if not project_dir:
                QMessageBox.warning(
                    self._win,
                    self._win.tr("Assemble failed"),
                    self._win.tr(
                        "No active project directory. Select a project first."
                    ),
                )
                return
            out_dir = Path(project_dir) / "target"
            out_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(out_dir / f"output.{fmt}")
            res = self._win._client.post(
                "/assemble",
                body={"output_path": output_path, "format": fmt},
                timeout=10.0,
            ) or {}
        except BackendError as exc:
            QMessageBox.warning(self._win, self._win.tr("Assemble failed"), str(exc))
            return
        if res.get("output_path"):
            self._win.statusBar().showMessage(
                self._win.tr("Output: {path}").format(path=res["output_path"]), 5000
            )

    def on_open_output_folder(self, output_path: str) -> None:
        """Open the directory containing the assembled file in the file explorer."""
        path = Path(output_path)
        target_dir = path.parent if path.is_file() else path
        if not target_dir.exists():
            QMessageBox.warning(
                self._win,
                self._win.tr("Folder not found"),
                self._win.tr(
                    "The output folder does not exist yet:\n{path}"
                ).format(path=str(target_dir)),
            )
            return
        try:
            if sys.platform == "win32":
                os.startfile(str(target_dir))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(target_dir)])
            else:
                subprocess.Popen(["xdg-open", str(target_dir)])
        except Exception as exc:
            QMessageBox.warning(
                self._win,
                self._win.tr("Could not open folder"),
                self._win.tr("Failed to open folder:\n{err}").format(err=str(exc)),
            )


# ---------------------------------------------------------------------------
# StatusRefresh
# ---------------------------------------------------------------------------


class StatusRefresh:
    """The 2-second health-poll cycle.

    Pulls ``/health``, updates the LLM badge, surfaces token usage on
    the status bar, and refreshes the pipeline state. Also detects
    backend offline → online transitions and re-polls the current page.
    """

    def __init__(self, win: "MainWindow"):
        self._win = win

    def refresh(self) -> None:
        if self._win._closing:
            return
        try:
            h = self._win._client.health()
        except BackendError:
            self.set_badge(self._win.tr("● Offline"))
            self._win._was_offline = True
            return
        if not h.get("ok"):
            self.set_badge(self._win.tr("● LLM: ?"))
            self._win._was_offline = True
            return
        # Backend is online — refresh the current page if we just
        # recovered from an offline period (e.g. backend restart).
        if self._win._was_offline:
            self._win._was_offline = False
            current = self._win._stack.currentWidget()
            if current is self._win._projects_tab:
                self._win._projects_tab.refresh()
            elif current is self._win._glossary_tab:
                self._win._glossary_tab.refresh()
            elif current is self._win._files_tab:
                self._win._files_tab.refresh()
        self.set_badge(self.format_llm_badge(h))
        self.update_statusbar_usage(h)
        self.refresh_pipeline_state()

    def set_badge(self, text: str) -> None:
        self._win._llm_badge.setText(text)
        self._win._llm_badge.setProperty("role", "muted")
        self._win._llm_badge.style().unpolish(self._win._llm_badge)
        self._win._llm_badge.style().polish(self._win._llm_badge)

    def format_llm_badge(self, health: dict[str, Any]) -> str:
        llm = health.get("llm") or {}
        nllb = health.get("nllb") or {}
        mode_map = {
            "local": self._win.tr("● Local only"),
            "cloud": self._win.tr("● Cloud"),
            "hybrid": self._win.tr("● Hybrid"),
            "offline": self._win.tr("● LLM: offline"),
        }
        mode = llm.get("mode", "offline")
        badge = mode_map.get(mode, self._win.tr("● LLM: ?"))
        if nllb.get("available"):
            badge += f" · {self._win.tr('NLLB ready')}"
        return badge

    def update_statusbar_usage(self, health: dict[str, Any]) -> None:
        llm = health.get("llm") or {}
        usage = llm.get("usage") or {}
        tokens = (usage.get("tokens_in") or 0) + (usage.get("tokens_out") or 0)
        if not tokens:
            self._win.statusBar().showMessage(self._win.tr("Backend connected."))
            return
        cost = usage.get("cost_usd") or 0.0
        tok_text = f"{tokens / 1000:.1f}k tok" if tokens >= 1000 else f"{tokens} tok"
        cost_text = f"${cost:.3f}" if cost > 0 else ""
        msg = f"{tok_text} · {cost_text}" if cost_text else tok_text
        self._win.statusBar().showMessage(msg)

    def refresh_pipeline_state(self) -> None:
        try:
            state = self._win._client.get("/pipeline/state", timeout=2.0) or {}
            self._win._pipeline_tab.update_pipeline_state(state)
            # Enable the HITL replay button only when there are
            # chunks actually waiting for a human answer.
            pending = int(state.get("pending_hltl", 0) or 0)
            self._win._pipeline_tab._replay_btn.setEnabled(pending > 0)
        except BackendError:
            pass


# ---------------------------------------------------------------------------
# UpdateChecker
# ---------------------------------------------------------------------------


class UpdateChecker:
    """Background + manual update checks and the update dialog.

    The main window owns the ``Updater``; this collaborator runs the
    checks on its timers and pops the non-modal ``UpdateDialog`` when a
    newer release is found. Never raises -- the timer slot must not
    crash the Qt event loop.
    """

    def __init__(self, win: "MainWindow"):
        self._win = win

    def check(self) -> None:
        """Background update check fired by ``QTimer.singleShot`` at boot.

        Never raises; on success it pops a non-modal :class:`UpdateDialog`
        and on no-update it stays silent. Skipped entirely in dev mode
        and when ``NOVELTRAD_SKIP_UPDATE=1``.
        """
        if self._win._closing:
            return
        try:
            if is_skipped() or not self._win._updater.should_check():
                return
            info = self._win._updater.check()
        except Exception as exc:  # noqa: BLE001 - timer slot must not raise
            logger.warning("auto-update check failed: %s", exc)
            return
        if info is None:
            return
        self.present_update_dialog(info)

    def on_manual_check(self) -> None:
        """Slot for the ``Check for updates`` button in SettingsTab."""
        if is_skipped() or not self._win._updater.should_check():
            QMessageBox.information(
                self._win,
                self._win.tr("Updates"),
                self._win.tr(
                    "Auto-update is disabled in this build (dev mode or "
                    "NOVELTRAD_SKIP_UPDATE=1)."
                ),
            )
            return
        try:
            info = self._win._updater.check()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(
                self._win,
                self._win.tr("Update check failed"),
                self._win.tr("Could not contact GitHub: {err}").format(err=exc),
            )
            return
        if info is None:
            QMessageBox.information(
                self._win,
                self._win.tr("Up to date"),
                self._win.tr(
                    "You are running the latest stable version "
                    "({version})."
                ).format(version=self._win._updater.current_version),
            )
            return
        self.present_update_dialog(info)

    def present_update_dialog(self, info) -> None:  # noqa: ANN001 - UpdateInfo
        if (
            self._win._pending_update_dialog is not None
            and self._win._pending_update_dialog.isVisible()
        ):
            self._win._pending_update_dialog.raise_()
            self._win._pending_update_dialog.activateWindow()
            return
        dlg = UpdateDialog(self._win._updater, info, parent=self._win)
        self._win._pending_update_dialog = dlg
        dlg.finished.connect(lambda _r: self.on_update_dialog_closed())
        dlg.show()

    def on_update_dialog_closed(self) -> None:
        self._win._pending_update_dialog = None