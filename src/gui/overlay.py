"""Selection overlay (CDC F1.c + F3.c).

Triggered by the global hotkey Ctrl+Alt+T. Flow:
  1. Simulate Ctrl+C to copy the current selection of the focused app.
  2. Read the clipboard.
  3. Show a small frameless overlay indicating "translation in progress".
  4. Run the 4-agent pipeline (in a QThread).
  5. On completion, put the result on the clipboard and simulate Ctrl+V to
     replace the selection.

Threading contract: translate_selection() may be called from the pynput
listener thread (the hotkey). It MUST NOT touch widgets directly — it marshals
execution to the UI thread via QMetaObject.invokeMethod. The pipeline runs in a
QThread that updates the overlay ONLY via Qt signals (queued connection).
"""

from __future__ import annotations

import time

from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from src.core.state import make_initial_state
from src.utils.config import Config


class OverlayWindow(QWidget):
    """Tiny frameless translucent popup that reports progress.

    All widget updates happen on the UI thread via the updateRequested signal
    (queued) or direct slot calls from the UI thread.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(260, 70)

        layout = QVBoxLayout(self)
        self.label = QLabel("⏳ Traduction…")
        f = QFont()
        f.setPointSize(11)
        f.setBold(True)
        self.label.setFont(f)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet(
            "QLabel { color: white; background-color: rgba(30,30,40,220);"
            "border-radius: 10px; padding: 16px; }"
        )
        layout.addWidget(self.label)

    @Slot(str)
    def set_message(self, msg: str) -> None:
        """UI-thread slot: set the overlay label text."""
        self.label.setText(msg)


class _SequenceWorker(QThread):
    """Runs capture → translate → paste off the UI thread, emitting UI signals."""

    message = Signal(str)
    hide_after = Signal(int)

    def __init__(self, config: Config) -> None:
        super().__init__()
        self.config = config

    def run(self) -> None:  # noqa: C901
        from pynput import keyboard as kb

        try:
            from src.core.agents import set_llm
            from src.core.graph import build_fast_graph, build_translation_graph
            from src.core.llm import get_llm
        except Exception as exc:  # noqa: BLE001
            self.message.emit(f"❌ {exc}"[:40])
            self.hide_after.emit(2000)
            return

        source = self._capture_selection(kb)
        if not source:
            self.message.emit("❌ Aucune sélection capturée")
            self.hide_after.emit(1200)
            return

        self.message.emit("🤖 Pipeline 4 agents…")

        result = ""
        try:
            llm = get_llm(
                provider=self.config.get("provider", "ollama"),
                model=self.config.get("model", "qwen2.5:7b"),
                base_url=(
                    self.config.get("ollama_host")
                    if self.config.get("provider", "ollama") == "ollama"
                    else self.config.get("remote_base_url") or None
                ),
                api_key=self.config.get("api_key") or None,
            )
            set_llm(llm)
            expert = self.config.get("expert_mode", True)
            graph = build_translation_graph() if expert else build_fast_graph()
            state = make_initial_state(
                source_text=source,
                source_lang=self.config.get("source_lang", "Anglais"),
                target_lang=self.config.get("target_lang", "Français"),
                profile=self.config.get("profile", "Général"),
            )
            final = graph.invoke(state, config={"recursion_limit": 25})
            result = final.get("final_text") or final.get("draft_translation") or ""
        except Exception as exc:  # noqa: BLE001
            set_llm(None)
            self.message.emit(f"❌ {exc}"[:40])
            self.hide_after.emit(2000)
            return
        finally:
            set_llm(None)

        # Paste the result back where the selection was.
        import pyperclip

        pyperclip.copy(result)
        self._paste_result(kb)
        self.message.emit("✅ Collé")
        self.hide_after.emit(900)

    @staticmethod
    def _capture_selection(kb) -> str:
        import pyperclip

        pyperclip.copy("")  # clear so we detect a real capture
        controller = kb.Controller()
        controller.press(kb.Key.ctrl)
        controller.press("c")
        controller.release("c")
        controller.release(kb.Key.ctrl)
        time.sleep(0.35)
        return pyperclip.paste().strip()

    @staticmethod
    def _paste_result(kb) -> None:
        controller = kb.Controller()
        controller.press(kb.Key.ctrl)
        controller.press("v")
        controller.release("v")
        controller.release(kb.Key.ctrl)
        time.sleep(0.2)


class SelectionTranslator(QWidget):
    """Orchestrates the capture → translate → paste sequence (F3.c).

    Inherits QWidget so it can host slots reached via QMetaObject.invokeMethod
    (the hotkey fires on the pynput thread; we marshal to the UI thread).
    translate_selection() is safe to call from ANY thread.
    """

    def __init__(self, config: Config) -> None:
        super().__init__()  # QWidget base (kept hidden; only the overlay shows)
        self.config = config
        self.overlay = OverlayWindow()
        self._worker: _SequenceWorker | None = None

    def translate_selection(self) -> None:
        """Entry point (called from the pynput thread or the tray). Marshals to UI."""
        # Bounce onto the UI thread — never touch widgets from a foreign thread.
        from PySide6.QtCore import QMetaObject
        from PySide6.QtCore import Qt as _Qt

        QMetaObject.invokeMethod(
            self, "_start_on_ui", _Qt.ConnectionType.QueuedConnection
        )

    @Slot()
    def _start_on_ui(self) -> None:
        """UI-thread slot: position the overlay and start the worker QThread."""
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            return

        screen = app.primaryScreen().geometry()
        self.overlay.move(
            screen.center().x() - self.overlay.width() // 2,
            screen.center().y() - self.overlay.height() // 2,
        )
        self.overlay.show()
        self.overlay.set_message("⏳ Capture de la sélection…")

        # Keep a strong reference so the QThread is not GC'd mid-run.
        self._worker = _SequenceWorker(self.config)
        self._worker.message.connect(self.overlay.set_message)
        self._worker.hide_after.connect(self._schedule_hide)
        self._worker.start()

    @Slot(int)
    def _schedule_hide(self, ms: int) -> None:
        """UI-thread slot: hide the overlay after a delay (no blocking sleep)."""
        from PySide6.QtCore import QTimer

        QTimer.singleShot(ms, self.overlay.hide)
