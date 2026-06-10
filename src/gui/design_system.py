"""Design system tokens for NovelTrad v4 GUI.

Centralises every visual constant (colors, spacing, radii, typography)
in one place so the rest of the GUI never hard-codes hex codes. Used
by `theme.py` to assemble a full `QApplication` stylesheet and by
individual widgets when they need a one-off rule.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class Spacing:
    xs: int = 4
    sm: int = 8
    md: int = 12
    lg: int = 16
    xl: int = 24
    xxl: int = 32


@dataclass(frozen=True)
class Radius:
    sm: int = 4
    md: int = 8
    lg: int = 12
    xl: int = 20


@dataclass(frozen=True)
class Typography:
    family: str = "Segoe UI, -apple-system, BlinkMacSystemFont, sans-serif"
    family_mono: str = "Cascadia Mono, Consolas, Menlo, monospace"
    size_xs: int = 9
    size_sm: int = 10
    size_md: int = 11
    size_lg: int = 13
    size_xl: int = 16
    size_xxl: int = 22
    weight_regular: int = 400
    weight_medium: int = 500
    weight_bold: int = 600


@dataclass(frozen=True)
class Palette:
    bg: str
    surface: str
    surface_alt: str
    surface_hover: str
    text: str
    text_muted: str
    text_inverse: str
    accent: str
    accent_hover: str
    accent_text: str
    success: str
    warning: str
    danger: str
    info: str
    border: str
    border_strong: str
    focus_ring: str
    selection: str
    overlay: str


LIGHT = Palette(
    bg="#f7f7fa",
    surface="#ffffff",
    surface_alt="#f0f0f4",
    surface_hover="#e8e8ee",
    text="#1c1c1f",
    text_muted="#5e5e66",
    text_inverse="#ffffff",
    accent="#2d6cdf",
    accent_hover="#245bbf",
    accent_text="#ffffff",
    success="#2f9e44",
    warning="#b3791a",
    danger="#c92a2a",
    info="#1c7ed6",
    border="#d9d9e0",
    border_strong="#9a9aa3",
    focus_ring="#3b82f6",
    selection="#cfe2ff",
    overlay="rgba(0, 0, 0, 0.45)",
)

DARK = Palette(
    bg="#0d0d10",
    surface="#16161a",
    surface_alt="#1f1f24",
    surface_hover="#26262c",
    text="#ececf1",
    text_muted="#9a9aa3",
    text_inverse="#1c1c1f",
    accent="#5b9dff",
    accent_hover="#7ab2ff",
    accent_text="#0d0d10",
    success="#51cf66",
    warning="#f59f00",
    danger="#ff6b6b",
    info="#4dabf7",
    border="#2a2a31",
    border_strong="#3a3a44",
    focus_ring="#7ab2ff",
    selection="#1a3554",
    overlay="rgba(0, 0, 0, 0.65)",
)

# WCAG AAA palette: ~7:1 contrast on white, ~12:1 on black.
HIGH_CONTRAST = Palette(
    bg="#000000",
    surface="#0a0a0a",
    surface_alt="#141414",
    surface_hover="#1f1f1f",
    text="#ffffff",
    text_muted="#d0d0d0",
    text_inverse="#000000",
    accent="#ffd400",
    accent_hover="#ffe34d",
    accent_text="#000000",
    success="#00ff7f",
    warning="#ffaa00",
    danger="#ff5555",
    info="#5cd6ff",
    border="#ffffff",
    border_strong="#ffffff",
    focus_ring="#ffd400",
    selection="#ffd400",
    overlay="rgba(0, 0, 0, 0.85)",
)


PALETTES: Mapping[str, Palette] = {
    "light": LIGHT,
    "dark": DARK,
    "high_contrast": HIGH_CONTRAST,
}


@dataclass(frozen=True)
class DesignTokens:
    spacing: Spacing = field(default_factory=Spacing)
    radius: Radius = field(default_factory=Radius)
    typography: Typography = field(default_factory=Typography)
    palette: Palette = DARK

    def stylesheet(self) -> str:
        """Build a complete `QApplication` stylesheet from the tokens."""
        p = self.palette
        s = self.spacing
        r = self.radius
        t = self.typography
        return f"""
        /* --- base --- */
        QWidget {{
            background-color: {p.bg};
            color: {p.text};
            font-family: "{t.family}";
            font-size: {t.size_md}pt;
        }}
        QMainWindow, QDialog {{
            background-color: {p.bg};
        }}
        QLabel {{
            color: {p.text};
            background: transparent;
        }}
        QLabel[role="muted"] {{
            color: {p.text_muted};
        }}
        QLabel[role="title"] {{
            font-size: {t.size_xxl}pt;
            font-weight: {t.weight_bold};
        }}
        QLabel[role="subtitle"] {{
            font-size: {t.size_lg}pt;
            color: {p.text_muted};
        }}

        /* --- inputs --- */
        QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox {{
            background-color: {p.surface};
            color: {p.text};
            border: 1px solid {p.border};
            border-radius: {r.sm}px;
            padding: {s.xs}px {s.sm}px;
            selection-background-color: {p.selection};
        }}
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
        QComboBox:focus, QSpinBox:focus {{
            border: 2px solid {p.focus_ring};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 24px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {p.surface};
            color: {p.text};
            border: 1px solid {p.border};
            selection-background-color: {p.selection};
        }}

        /* --- buttons --- */
        QPushButton {{
            background-color: {p.surface_alt};
            color: {p.text};
            border: 1px solid {p.border};
            border-radius: {r.sm}px;
            padding: {s.sm}px {s.md}px;
            min-height: 24px;
            min-width: 80px;
        }}
        QPushButton:hover {{
            background-color: {p.surface_hover};
        }}
        QPushButton:pressed {{
            background-color: {p.surface_alt};
        }}
        QPushButton:focus {{
            border: 2px solid {p.focus_ring};
        }}
        QPushButton:disabled {{
            color: {p.text_muted};
            background-color: {p.surface};
        }}
        QPushButton[role="primary"] {{
            background-color: {p.accent};
            color: {p.accent_text};
            border: 1px solid {p.accent};
            font-weight: {t.weight_medium};
        }}
        QPushButton[role="primary"]:hover {{
            background-color: {p.accent_hover};
            border-color: {p.accent_hover};
        }}
        QPushButton[role="danger"] {{
            background-color: {p.danger};
            color: {p.text_inverse};
            border: 1px solid {p.danger};
        }}
        QPushButton[role="ghost"] {{
            background-color: transparent;
            border: 1px solid transparent;
        }}
        QPushButton[role="ghost"]:hover {{
            background-color: {p.surface_hover};
        }}

        /* --- lists & views --- */
        QListView, QTreeView, QListWidget, QTreeWidget {{
            background-color: {p.surface};
            color: {p.text};
            border: 1px solid {p.border};
            border-radius: {r.sm}px;
            outline: 0;
        }}
        QListView::item, QListWidget::item {{
            padding: {s.sm}px;
            border-radius: {r.sm}px;
        }}
        QListView::item:selected, QListWidget::item:selected {{
            background-color: {p.selection};
            color: {p.text};
        }}
        QListView::item:hover, QListWidget::item:hover {{
            background-color: {p.surface_hover};
        }}

        /* --- tabs --- */
        QTabWidget::pane {{
            border: 1px solid {p.border};
            background-color: {p.surface};
            border-radius: {r.md}px;
        }}
        QTabBar::tab {{
            background-color: {p.surface_alt};
            color: {p.text_muted};
            padding: {s.sm}px {s.md}px;
            border: 1px solid {p.border};
            border-bottom: none;
            border-top-left-radius: {r.sm}px;
            border-top-right-radius: {r.sm}px;
        }}
        QTabBar::tab:selected {{
            background-color: {p.surface};
            color: {p.text};
        }}

        /* --- progress --- */
        QProgressBar {{
            background-color: {p.surface_alt};
            color: {p.text};
            border: 1px solid {p.border};
            border-radius: {r.sm}px;
            text-align: center;
            min-height: 18px;
        }}
        QProgressBar::chunk {{
            background-color: {p.accent};
            border-radius: {r.sm}px;
        }}

        /* --- status / tooltip --- */
        QStatusBar {{
            background-color: {p.surface_alt};
            color: {p.text_muted};
        }}
        QToolTip {{
            background-color: {p.surface};
            color: {p.text};
            border: 1px solid {p.border_strong};
            padding: {s.xs}px {s.sm}px;
            border-radius: {r.sm}px;
        }}

        /* --- scrollbar --- */
        QScrollBar:vertical {{
            background: {p.surface_alt};
            width: 12px;
            margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {p.border_strong};
            min-height: 24px;
            border-radius: 6px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {p.text_muted};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        QScrollBar:horizontal {{
            background: {p.surface_alt};
            height: 12px;
        }}
        QScrollBar::handle:horizontal {{
            background: {p.border_strong};
            min-width: 24px;
            border-radius: 6px;
        }}

        /* --- menu / splitter / frame --- */
        QMenu {{
            background-color: {p.surface};
            color: {p.text};
            border: 1px solid {p.border};
        }}
        QMenu::item:selected {{
            background-color: {p.selection};
        }}
        QSplitter::handle {{
            background-color: {p.border};
        }}
        QFrame[role="card"] {{
            background-color: {p.surface};
            border: 1px solid {p.border};
            border-radius: {r.md}px;
        }}
        QFrame[role="dropzone"] {{
            background-color: {p.surface_alt};
            border: 2px dashed {p.border_strong};
            border-radius: {r.lg}px;
        }}
        QFrame[role="dropzone"][active="true"] {{
            border-color: {p.accent};
            background-color: {p.surface_hover};
        }}
        """


def get_palette(name: str) -> Palette:
    """Return the named palette, falling back to DARK on unknown input."""
    return PALETTES.get(name, DARK)


__all__ = [
    "DesignTokens",
    "Palette",
    "PALETTES",
    "Spacing",
    "Radius",
    "Typography",
    "LIGHT",
    "DARK",
    "HIGH_CONTRAST",
    "get_palette",
]
