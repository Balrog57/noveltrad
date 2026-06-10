"""Theme manager — apply light/dark/high_contrast globally."""

from __future__ import annotations

from typing import Iterable

from PyQt6.QtCore import QObject, QSettings, pyqtSignal
from PyQt6.QtWidgets import QApplication

from .design_system import DARK, DesignTokens, get_palette


VALID_THEMES: tuple[str, ...] = ("light", "dark", "high_contrast")


class ThemeManager(QObject):
    """Holds the active theme and re-pushes the stylesheet on change."""

    themeChanged = pyqtSignal(str)

    _instance: "ThemeManager | None" = None

    def __init__(self) -> None:
        super().__init__()
        self._tokens = DesignTokens(palette=DARK)
        self._current_name = "dark"
        self._listeners: list[QObject] = []

    @classmethod
    def instance(cls) -> "ThemeManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def current(self) -> str:
        return self._current_name

    @property
    def tokens(self) -> DesignTokens:
        return self._tokens

    def apply(self, app: QApplication, theme_name: str) -> None:
        """Set the global stylesheet and notify listeners."""
        if theme_name not in VALID_THEMES:
            theme_name = "dark"
        palette = get_palette(theme_name)
        self._tokens = DesignTokens(palette=palette)
        self._current_name = theme_name
        app.setStyleSheet("")
        app.setStyleSheet(self._tokens.stylesheet())
        # Force every top-level widget to repolish so dynamic properties
        # (e.g. [role="primary"]) refresh.
        for w in app.topLevelWidgets():
            app.style().polish(w)
        self.themeChanged.emit(theme_name)

    def cycle(self, app: QApplication) -> str:
        """Switch to the next theme in VALID_THEMES, return the new name."""
        idx = VALID_THEMES.index(self._current_name)
        nxt = VALID_THEMES[(idx + 1) % len(VALID_THEMES)]
        self.apply(app, nxt)
        return nxt

    def save_to(self, settings: QSettings) -> None:
        settings.setValue("UI/theme", self._current_name)

    def restore_from(self, settings: QSettings, app: QApplication) -> str:
        name = settings.value("UI/theme", "dark", type=str)
        if name not in VALID_THEMES:
            name = "dark"
        self.apply(app, name)
        return name


__all__ = ["ThemeManager", "VALID_THEMES"]
