"""Theme handling (SDD 13.2, 13.14): light, dark, sepia.

Streamlit renders its widgets with CSS variables; forcing plain CSS on
.stApp leaves widgets in the browser-default palette. A complete theme must
redefine the Streamlit variables and target the sidebar, header, inputs,
selectboxes, buttons and text so every surface follows light/dark/sepia.
"""

from __future__ import annotations

_THEMES = {
    "light": {
        "primary": "#0d9488",
        "background": "#f7f8fa",
        "secondary": "#ffffff",
        "tertiary": "#eef1f4",
        "text": "#262730",
        "muted": "#6b7280",
        "border": "#d1d5db",
        "sidebar": "#ffffff",
        "hover": "#e5e7eb",
    },
    "dark": {
        "primary": "#2dd4bf",
        "background": "#141420",
        "secondary": "#1e1e2e",
        "tertiary": "#2a2a3e",
        "text": "#e5e7eb",
        "muted": "#9ca3af",
        "border": "#3f3f56",
        "sidebar": "#181826",
        "hover": "#2f2f44",
    },
    "sepia": {
        "primary": "#8a5a2b",
        "background": "#f4ecd8",
        "secondary": "#faf4e4",
        "tertiary": "#e9ddc2",
        "text": "#3b2f1c",
        "muted": "#7a6a4f",
        "border": "#cbbfa0",
        "sidebar": "#efe5cd",
        "hover": "#e3d5b4",
    },
}


def _css(theme: str) -> str:
    c = _THEMES.get(theme, _THEMES["light"])
    return f"""
    <style>
    .stApp {{
        --primary-color: {c["primary"]};
        --background-color: {c["background"]};
        --secondary-background-color: {c["secondary"]};
        --text-color: {c["text"]};
        --font: "Source Sans Pro", sans-serif;
        background-color: {c["background"]};
        color: {c["text"]};
    }}

    /* sidebar */
    [data-testid="stSidebar"] {{
        background-color: {c["sidebar"]};
        border-right: 1px solid {c["border"]};
    }}
    [data-testid="stSidebar"] * {{ color: {c["text"]} !important; }}

    /* header */
    [data-testid="stHeader"] {{
        background: transparent;
    }}

    /* inputs, textareas, selectboxes, multiselect */
    .stTextInput input, .stTextArea textarea,
    .stSelectbox div[data-baseweb="select"] > div,
    .stNumberInput input, .stDateInput input {{
        background-color: {c["secondary"]};
        color: {c["text"]};
        border-color: {c["border"]};
    }}
    .stTextInput input::placeholder, .stTextArea textarea::placeholder {{
        color: {c["muted"]};
    }}
    .stSelectbox div[data-baseweb="select"] * {{
        color: {c["text"]};
    }}

    /* dropdown menu */
    div[data-baseweb="popover"] ul, div[data-baseweb="menu"] {{
        background-color: {c["secondary"]};
        color: {c["text"]};
    }}
    div[data-baseweb="menu"] li:hover {{
        background-color: {c["hover"]};
    }}

    /* primary buttons */
    .stButton button[kind="primary"] {{
        background-color: {c["primary"]};
        color: {c["secondary"]};
        border: none;
    }}
    .stButton button[kind="primary"]:hover {{
        background-color: {c["primary"]};
        filter: brightness(1.1);
        color: {c["secondary"]};
    }}

    /* secondary buttons */
    .stButton button[kind="secondary"] {{
        background-color: {c["secondary"]};
        color: {c["primary"]};
        border: 1px solid {c["primary"]};
    }}
    .stButton button[kind="secondary"]:hover {{
        background-color: {c["tertiary"]};
        color: {c["primary"]};
    }}

    /* generic buttons fallback */
    .stButton button {{
        background-color: {c["secondary"]};
        color: {c["text"]};
        border: 1px solid {c["border"]};
    }}
    .stButton button:hover {{
        background-color: {c["hover"]};
        color: {c["text"]};
    }}

    /* checkboxes, radios */
    .stCheckbox label, .stRadio label {{
        color: {c["text"]};
    }}

    /* expanders and containers */
    .stExpander, [data-testid="stExpander"] {{
        background-color: {c["secondary"]};
        border: 1px solid {c["border"]};
        border-radius: 8px;
    }}
    .stExpander summary, [data-testid="stExpander"] summary {{
        color: {c["text"]};
    }}
    [data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: {c["secondary"]};
        border-color: {c["border"]};
    }}

    /* captions, info, code */
    .stCaption, .stMarkdown p, .stMarkdown li, .stMarkdown h1,
    .stMarkdown h2, .stMarkdown h3, .stMarkdown h4, .stMarkdown h5 {{
        color: {c["text"]};
    }}
    .stMarkdown {{ color: {c["text"]}; }}

    /* progress bars */
    .stProgress div[role="progressbar"] > div {{
        background-color: {c["primary"]};
    }}

    /* metrics */
    [data-testid="stMetricValue"], [data-testid="stMetricLabel"] {{
        color: {c["text"]};
    }}

    /* tabs */
    .stTabs [data-baseweb="tab-list"] button {{
        color: {c["muted"]};
    }}
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {{
        color: {c["primary"]};
        border-bottom-color: {c["primary"]};
    }}

    /* success/error/info toasts keep readable text */
    .stAlert {{
        color: {c["text"]};
    }}
    </style>
    """


def apply_theme(theme: str) -> None:
    """Inject the complete theme CSS into the running Streamlit page."""
    import streamlit as st

    st.markdown(_css(theme), unsafe_allow_html=True)


def valid_theme(value: str) -> bool:
    return value in _THEMES
