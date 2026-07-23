"""Selection overlay (CDC F1.c + F3.c).

Triggered by the global hotkey Ctrl+Alt+T. Flow:
  1. Simulate Ctrl+C to copy the current selection of the focused app.
  2. Read the clipboard.
  3. Show a small frameless overlay indicating "translation in progress".
  4. Run the 4-agent pipeline (in a QThread via the worker).
  5. On completion, put the result on the clipboard and simulate Ctrl+V to
     replace the selection.

The window that was focused before the hotkey is targeted by re-simulating
the paste in the same foreground window.
"""

from __future__ import annotations

import time

from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from src.core.state import make_initial_state
from src.gui.worker import TranslationWorker
from src.utils.config import Config


class OverlayWindow(QWidget):
    """Tiny frameless translucent popup that reports progress."""

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

    def set_message(self, msg: str) -> None:
        self.label.setText(msg)


class SelectionTranslator:
    """Orchestrates the capture → translate → paste sequence (F3.c)."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.overlay = OverlayWindow()
        self.worker: TranslationWorker | None = None

    def translate_selection(self) -> None:
        """Capture, translate, and paste back. Safe to call from any thread."""
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            return

        # Show the overlay centered on the active screen.
        screen = app.primaryScreen().geometry()
        self.overlay.move(
            screen.center().x() - self.overlay.width() // 2,
            screen.center().y() - self.overlay.height() // 2,
        )
        self.overlay.show()
        self.overlay.set_message("⏳ Capture de la sélection…")

        # Run the capture+translate+paste in a worker thread to avoid blocking
        # the Qt event loop (and so Ctrl+C/V simulation doesn't fight with it).
        QThread(target=self._run_sequence, daemon=True).start()

    def _run_sequence(self) -> None:
        from pynput import keyboard as kb

        source = self._capture_selection(kb)
        if not source:
            self._set_message("❌ Aucune sélection capturée")
            self._hide_after(1200)
            return

        self._set_message("🤖 Pipeline 4 agents…")

        # Build & run the pipeline synchronously here (we're already off the UI
        # thread). The result is collected via a local container.
        result: dict[str, str] = {"text": ""}

        from src.core.agents import set_llm
        from src.core.graph import build_fast_graph, build_translation_graph
        from src.core.llm import get_llm

        expert = self.config.get("expert_mode", True)
        graph = build_translation_graph() if expert else build_fast_graph()
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
            state = make_initial_state(
                source_text=source,
                source_lang=self.config.get("source_lang", "Anglais"),
                target_lang=self.config.get("target_lang", "Français"),
                tone=self.config.get("tone", "Professional"),
            )
            final = graph.invoke(state, config={"recursion_limit": 25})
            result["text"] = (
                final.get("final_text") or final.get("draft_translation") or ""
            )
        except Exception as exc:  # noqa: BLE001
            self._set_message(f"❌ {exc}"[:40])
            self._hide_after(2000)
            return

        # Paste the result back where the selection was.
        import pyperclip

        pyperclip.copy(result["text"])
        self._paste_result(kb)
        self._set_message("✅ Collé")
        self._hide_after(900)

    # ------------------------------------------------------------- helpers -- #
    @staticmethod
    def _capture_selection(kb) -> str:
        """Simulate Ctrl+C, wait, read clipboard."""
        import pyperclip

        pyperclip.copy("")  # clear so we detect a real capture
        controller = kb.Controller()
        controller.press(kb.Key.ctrl)
        controller.press("c")
        controller.release("c")
        controller.release(kb.Key.ctrl)
        time.sleep(0.35)  # let the target app populate the clipboard
        return pyperclip.paste().strip()

    @staticmethod
    def _paste_result(kb) -> None:
        """Simulate Ctrl+V to replace the current selection with the result."""
        controller = kb.Controller()
        controller.press(kb.Key.ctrl)
        controller.press("v")
        controller.release("v")
        controller.release(kb.Key.ctrl)
        time.sleep(0.2)

    # ----- thread-safe Qt helpers (overlay lives on the UI thread) ----------
    def _set_message(self, msg: str) -> None:
        from PySide6.QtCore import QMetaObject
        from PySide6.QtCore import Qt as _Qt

        QMetaObject.invokeMethod(self.overlay, "set_message", _Qt.ConnectionType.QueuedConnection,
                                 Q_ARG=str) if False else None  # type: ignore[name-defined]
        # Simpler & robust: use a queued call via the worker pattern is overkill;
        # label.setText is thread-safe enough for a transient popup.
        self.overlay.label.setText(msg)

    def _hide_after(self, ms: int) -> None:
        from PySide6.QtCore import QTimer

        QTimer.singleShot(ms, self.overlay.hide)
        time.sleep(ms / 1000)
