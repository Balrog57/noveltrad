"""Theme handling (SDD 13.2, 13.14): light, dark, sepia.

Streamlit renders its widgets with its own CSS variables. Forcing plain
`color`/`background-color` on `.stApp` leaves inputs and buttons in the
browser-default (dark) palette, producing invisible fields. The correct
approach is to redefine the Streamlit CSS variables used by every widget:
`--primary-color`, `--background-color`, `--secondary-background-color`
and `--text-color`.
"""

from __future__ import annotations

_THEMES = {
    "light": {
        "primary": "#0d9488",
        "background": "#ffffff",
        "secondary": "#f4f6f8",
        "text": "#262730",
    },
    "dark": {
        "primary": "#2dd4bf",
        "background": "#1e1e2e",
        "secondary": "#2a2a3e",
        "text": "#e0e0e6",
    },
    "sepia": {
        "primary": "#8a5a2b",
        "background": "#f4ecd8",
        "secondary": "#e9ddc2",
        "text": "#3b2f1c",
    },
}


def apply_theme(theme: str) -> None:
    """Inject Streamlit CSS variables for the requested theme."""
    import streamlit as st

    colors = _THEMES.get(theme, _THEMES["light"])
    st.markdown(
        f"""
        <style>
        .stApp {{
            --primary-color: {colors["primary"]};
            --background-color: {colors["background"]};
            --secondary-background-color: {colors["secondary"]};
            --text-color: {colors["text"]};
        }}
        .stApp input, .stApp textarea {{
            background-color: {colors["secondary"]};
            color: {colors["text"]};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def valid_theme(value: str) -> bool:
    return value in _THEMES
