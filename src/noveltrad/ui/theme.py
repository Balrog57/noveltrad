"""Theme handling (SDD 13.2, 13.14): light, dark, sepia."""

from __future__ import annotations

_THEMES = {
    "light": {"background": "#ffffff", "text": "#1a1a1a"},
    "dark": {"background": "#1e1e2e", "text": "#e0e0e0"},
    "sepia": {"background": "#f4ecd8", "text": "#3b2f1c"},
}


def apply_theme(theme: str) -> None:
    """Inject theme CSS into the running Streamlit page."""
    import streamlit as st

    colors = _THEMES.get(theme, _THEMES["light"])
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-color: {colors["background"]};
            color: {colors["text"]};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def valid_theme(value: str) -> bool:
    return value in _THEMES
