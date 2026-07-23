"""Global hotkey listener (CDC F1.c + Phase 1 'pynput').

Registers Ctrl+Alt+T system-wide so the selection overlay can be triggered even
when another application has focus. Runs pynput in a daemon thread.

NOTE: on Windows, global hotkeys that synthesize Ctrl+C/Ctrl+V keystrokes may
require the app to run with normal user privileges (UAC-elevated target windows
cannot be automated from a non-elevated process).
"""

from __future__ import annotations

import threading
from collections.abc import Callable

from pynput import keyboard

# CDC F1.c: Ctrl + Alt + T (as a set of canonical key combinations).
HOTKEY_KEYS = keyboard.HotKey.parse("<ctrl>+<alt>+t")


class GlobalHotkey:
    """Wraps a pynput listener that fires a callback on Ctrl+Alt+T."""

    def __init__(self, callback: Callable[[], None]) -> None:
        self.callback = callback
        self._listener: keyboard.Listener | None = None
        self._thread: threading.Thread | None = None
        self._current = set()  # currently pressed canonical keys

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        self._listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        self._listener.start()
        self._listener.join()

    def _on_press(self, key) -> None:
        try:
            canonical = self._listener.canonical(key) if self._listener else key  # type: ignore[union-attr]
        except Exception:
            canonical = key
        self._current.add(canonical)
        if self._current == set(HOTKEY_KEYS):
            self._current.clear()
            try:
                self.callback()
            except Exception:  # noqa: BLE001 - never kill the listener thread
                pass

    def _on_release(self, key) -> None:
        try:
            canonical = self._listener.canonical(key) if self._listener else key  # type: ignore[union-attr]
        except Exception:
            canonical = key
        self._current.discard(canonical)

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
        self._thread = None
