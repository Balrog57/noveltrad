"""Material Design theme handling (SDD 13.2, 13.14): light, dark, sepia.

Applies a complete Material Design palette — Roboto, elevation shadows,
rounded corners, consistent inputs/buttons — by redefining every Streamlit
CSS variable plus targeted overrides for widgets that ignore variables.
Every surface follows the selected theme so no element stays unreadable.
"""

from __future__ import annotations

_THEMES = {
    "light": {
        "primary": "#0d9488",
        "primary_dark": "#0f766e",
        "background": "#f4f6f8",
        "surface": "#ffffff",
        "surface_variant": "#eef1f4",
        "text": "#1a1c1e",
        "text_secondary": "#5f6368",
        "on_primary": "#ffffff",
        "border": "#d1d5db",
        "sidebar": "#ffffff",
        "hover": "#e5e7eb",
        "error": "#b3261e",
        "success": "#2e7d32",
        "warning": "#b26a00",
    },
    "dark": {
        "primary": "#4dd0c4",
        "primary_dark": "#26a69a",
        "background": "#121212",
        "surface": "#1e1e2e",
        "surface_variant": "#2a2a3e",
        "text": "#e4e6eb",
        "text_secondary": "#9aa0a6",
        "on_primary": "#00332e",
        "border": "#3f3f56",
        "sidebar": "#181826",
        "hover": "#2f2f44",
        "error": "#f2b8b5",
        "success": "#81c995",
        "warning": "#fdd663",
    },
    "sepia": {
        "primary": "#8a5a2b",
        "primary_dark": "#6d4420",
        "background": "#f4ecd8",
        "surface": "#faf4e4",
        "surface_variant": "#e9ddc2",
        "text": "#3b2f1c",
        "text_secondary": "#7a6a4f",
        "on_primary": "#fff8ec",
        "border": "#cbbfa0",
        "sidebar": "#efe5cd",
        "hover": "#e3d5b4",
        "error": "#9c3b2e",
        "success": "#4d6b3a",
        "warning": "#8a5a2b",
    },
}


def _css(theme: str) -> str:
    c = _THEMES.get(theme, _THEMES["light"])
    return f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');

    .stApp {{
        --primary-color: {c["primary"]};
        --background-color: {c["background"]};
        --secondary-background-color: {c["surface"]};
        --text-color: {c["text"]};
        --font: 'Roboto', sans-serif;
        background-color: {c["background"]};
        color: {c["text"]};
        /* font-family is applied per-widget below, never globally: the global
           rule would override Streamlit's Material Icons glyph spans */
    }}

    /* ---------- Material icons: Streamlit ships "Material Symbols Rounded" ---------- */
    .material-icons, .material-icons-extended, .material-symbols-rounded,
    [data-testid="stIconMaterial"], [data-testid="stIcon"],
    span[class*="material-symbols"],
    span[class*="material-icons"],
    button[aria-label*="visibility"] span,
    [data-testid="stSidebarCollapsedControl"] span {{
        font-family: "Material Symbols Rounded", "Material Icons" !important;
        color: {c["text_secondary"]} !important;
        font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
    }}
    /* password visibility toggle */
    [data-testid="stWidgetLabel"] span[class*="st-emotion"] {{
        font-family: "Material Symbols Rounded", "Material Icons" !important;
    }}

    /* ---------- global text ---------- */
    .stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown h1,
    .stMarkdown h2, .stMarkdown h3, .stMarkdown h4, .stMarkdown h5,
    .stCaption, .stTitle, .stSubheader, .stHeader,
    .stTextInput input, .stTextArea textarea, .stNumberInput input,
    .stSelectbox [data-baseweb="select"] > div,
    .stButton button, .stDownloadButton button {{
        font-family: 'Roboto', sans-serif;
        color: {c["text"]} !important;
    }}
    .stMarkdown a {{ color: {c["primary"]} !important; }}
    code, .stCode, pre {{
        background-color: {c["surface_variant"]} !important;
        color: {c["text"]} !important;
    }}

    /* ---------- sidebar ---------- */
    [data-testid="stSidebar"] {{
        background-color: {c["sidebar"]};
        border-right: 1px solid {c["border"]};
    }}
    [data-testid="stSidebar"] * {{ color: {c["text"]} !important; }}
    [data-testid="stSidebar"] .stMarkdown h1 {{
        color: {c["primary"]} !important;
        font-weight: 700;
    }}

    /* ---------- header ---------- */
    [data-testid="stHeader"] {{
        background: transparent;
    }}

    /* ---------- text inputs / textareas ---------- */
    .stTextInput input, .stTextArea textarea, .stNumberInput input {{
        background-color: {c["surface"]} !important;
        color: {c["text"]} !important;
        border: 1px solid {c["border"]} !important;
        border-radius: 4px !important;
        caret-color: {c["primary"]};
    }}
    .stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus {{
        border-color: {c["primary"]} !important;
        box-shadow: 0 0 0 1px {c["primary"]} !important;
    }}
    .stTextInput input::placeholder, .stTextArea textarea::placeholder {{
        color: {c["text_secondary"]} !important;
    }}
    input[type="password"] {{
        background-color: {c["surface"]} !important;
        color: {c["text"]} !important;
        border: 1px solid {c["border"]} !important;
        border-radius: 4px !important;
    }}

    /* ---------- selectbox / dropdown ---------- */
    .stSelectbox [data-baseweb="select"] > div {{
        background-color: {c["surface"]} !important;
        border-color: {c["border"]} !important;
        border-radius: 4px !important;
    }}
    .stSelectbox [data-baseweb="select"] * {{
        color: {c["text"]} !important;
    }}
    .stSelectbox [data-baseweb="select"] svg {{
        fill: {c["text_secondary"]} !important;
    }}
    div[data-baseweb="popover"] ul, div[data-baseweb="menu"], div[data-baseweb="popover"] {{
        background-color: {c["surface"]} !important;
        color: {c["text"]} !important;
    }}
    div[data-baseweb="menu"] li {{
        color: {c["text"]} !important;
    }}
    div[data-baseweb="menu"] li:hover {{
        background-color: {c["hover"]} !important;
    }}
    div[data-baseweb="menu"] li[aria-selected="true"] {{
        background-color: {c["surface_variant"]} !important;
        color: {c["primary"]} !important;
    }}

    /* ---------- multi-select / chips ---------- */
    .stMultiSelect [data-baseweb="tag"] {{
        background-color: {c["primary"]} !important;
        color: {c["on_primary"]} !important;
        border-radius: 16px !important;
    }}
    .stMultiSelect [data-baseweb="tag"] span {{ color: {c["on_primary"]} !important; }}

    /* ---------- buttons (Material) ---------- */
    .stButton button, .stDownloadButton button {{
        background-color: {c["surface"]};
        color: {c["primary"]};
        border: 1px solid {c["primary"]};
        border-radius: 4px;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.08);
        transition: box-shadow 0.2s ease, background-color 0.2s ease;
    }}
    .stButton button:hover, .stDownloadButton button:hover {{
        background-color: {c["hover"]};
        box-shadow: 0 2px 4px rgba(0,0,0,0.16);
    }}
    .stButton button:active, .stDownloadButton button:active {{
        background-color: {c["surface_variant"]};
        box-shadow: 0 1px 1px rgba(0,0,0,0.12);
    }}
    .stButton button[kind="primary"], .stDownloadButton button[kind="primary"] {{
        background-color: {c["primary"]};
        color: {c["on_primary"]};
        border: none;
        box-shadow: 0 1px 3px rgba(0,0,0,0.2);
    }}
    .stButton button[kind="primary"]:hover, .stDownloadButton button[kind="primary"]:hover {{
        background-color: {c["primary_dark"]};
        color: {c["on_primary"]};
        box-shadow: 0 3px 6px rgba(0,0,0,0.24);
    }}

    /* ---------- radio / checkbox ---------- */
    .stRadio label, .stCheckbox label {{
        color: {c["text"]} !important;
    }}
    .stCheckbox [data-testid="stCheckbox"] label p {{ color: {c["text"]} !important; }}
    .stRadio [data-testid="stRadio"] label p {{ color: {c["text"]} !important; }}
    .stRadio div[role="radiogroup"] > label > div:first-child > div {{
        background-color: {c["surface"]} !important;
        border-color: {c["primary"]} !important;
    }}

    /* ---------- slider ---------- */
    .stSlider [data-testid="stSliderThumbValue"] {{
        background-color: {c["primary"]} !important;
        color: {c["on_primary"]} !important;
    }}
    .stSlider [role="slider"] {{ background-color: {c["primary"]} !important; }}
    .stSlider [data-testid="stSlider"] > div > div > div:nth-child(1) {{
        background: {c["primary"]} !important;
    }}

    /* ---------- "Press Enter to apply" tooltip: hide it ---------- */
    [data-testid="stWidgetHelp"] span,
    [data-testid="stTooltipContent"] span,
    div[data-testid="stTooltipContent"] {{
        display: none !important;
    }}

    /* ---------- file uploader ---------- */
    [data-testid="stFileUploader"] {{
        background-color: {c["surface"]} !important;
        border: 1px dashed {c["primary"]} !important;
        border-radius: 4px !important;
        color: {c["text"]} !important;
    }}
    [data-testid="stFileUploader"] * {{ color: {c["text"]} !important; }}
    [data-testid="stFileUploaderDropzone"] {{
        background-color: {c["surface"]} !important;
    }}
    [data-testid="stFileUploaderDropzone"]:hover {{
        background-color: {c["hover"]} !important;
    }}

    /* ---------- expanders / cards ---------- */
    .stExpander, [data-testid="stExpander"] {{
        background-color: {c["surface"]};
        border: 1px solid {c["border"]};
        border-radius: 8px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.06);
    }}
    .stExpander summary, [data-testid="stExpander"] summary {{
        color: {c["text"]} !important;
        font-weight: 500;
    }}
    [data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: {c["surface"]};
        border-color: {c["border"]};
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }}

    /* ---------- tabs ---------- */
    .stTabs [data-baseweb="tab-list"] button {{
        color: {c["text_secondary"]} !important;
    }}
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {{
        color: {c["primary"]} !important;
        border-bottom-color: {c["primary"]} !important;
    }}

    /* ---------- progress / metric ---------- */
    .stProgress div[role="progressbar"] > div {{
        background-color: {c["primary"]} !important;
    }}
    [data-testid="stMetricValue"], [data-testid="stMetricLabel"], [data-testid="stMetricDelta"] {{
        color: {c["text"]} !important;
    }}

    /* ---------- alerts ---------- */
    .stAlert {{ color: {c["text"]} !important; }}
    [data-testid="stAlert"] {{ color: {c["text"]} !important; }}

    /* ---------- dataframes ---------- */
    [data-testid="stDataFrame"], [data-testid="stTable"] {{
        color: {c["text"]} !important;
    }}
    [data-testid="stDataFrame"] * {{ color: {c["text"]} !important; }}

    /* ---------- spinner ---------- */
    [data-testid="stSpinner"] {{ color: {c["text"]} !important; }}
    [data-testid="stSpinner"] * {{ color: {c["text"]} !important; }}

    /* ---------- horizontal rule ---------- */
    hr {{ border-color: {c["border"]} !important; }}

    /* ---------- tooltips ---------- */
    [data-testid="stTooltip"] {{ color: {c["text"]} !important; }}

    /* ---------- toast ---------- */
    [data-testid="stToast"] {{
        background-color: {c["surface"]} !important;
        color: {c["text"]} !important;
    }}

    /* ---------- theme-specific text enforcement ---------- */
    .stApp [data-testid="stWidgetLabel"],
    .stApp [data-testid="stWidgetLabel"] p,
    .stApp [data-testid="stWidgetLabel"] span,
    .stApp label p,
    .stApp .stMarkdown p,
    .stApp .stMarkdown span,
    .stApp [data-testid="stCaptionContainer"] p,
    .stApp [data-testid="stExpander"] summary,
    .stApp .stExpander summary,
    .stApp [data-testid="stSelectbox"] input,
    .stApp [data-testid="stMultiSelect"] input,
    .stApp [data-testid="stNumberInput"] input,
    .stApp .stTextInput label,
    .stApp .stNumberInput label,
    .stApp .stTextArea label,
    .stApp .stDateInput label {{
        color: {c["text"]} !important;
    }}

    /* selectbox selected value */
    .stApp [data-baseweb="select"] span {{
        color: {c["text"]} !important;
    }}

    /* collapsed sidebar toggle */
    .stApp [data-testid="stSidebarCollapsedControl"] {{
        color: {c["text"]} !important;
    }}
    .stApp [data-testid="stSidebarCollapsedControl"] .material-icons,
    .stApp [data-testid="stSidebarCollapsedControl"] span {{
        color: {c["text"]} !important;
    }}

    /* markdown emphasis and bullets */
    .stApp .stMarkdown strong {{ color: {c["text"]} !important; }}
    .stApp .stMarkdown em {{ color: {c["text"]} !important; }}
    .stApp .stMarkdown ul li, .stApp .stMarkdown ol li {{ color: {c["text"]} !important; }}

    /* metric */
    .stApp [data-testid="stMetric"] * {{ color: {c["text"]} !important; }}
    .stApp [data-testid="stMetricLabel"] * {{ color: {c["text_secondary"]} !important; }}

    /* dataframe cells */
    .stApp [data-testid="stDataFrame"] .stMarkdown p {{ color: {c["text"]} !important; }}
    .stApp [data-testid="stTable"] * {{ color: {c["text"]} !important; }}

    /* dialog/popover */
    .stApp [data-testid="stDialog"] * {{ color: {c["text"]} !important; }}
    .stApp [data-testid="stPopover"] * {{ color: {c["text"]} !important; }}
    </style>
    """


def apply_theme(theme: str) -> None:
    """Inject the Material Design theme CSS into the running Streamlit page."""
    import streamlit as st

    st.markdown(_css(theme), unsafe_allow_html=True)


def header_style(theme: str) -> str:
    """Inline style for the sidebar header band: darker than the surface,
    with text color adapting to the theme."""
    header_colors = {
        "light": {"bg": "#0f766e", "text": "#ffffff"},
        "dark": {"bg": "#0b3d38", "text": "#e0f2f1"},
        "sepia": {"bg": "#6d4420", "text": "#fff8ec"},
    }
    colors = header_colors.get(theme, header_colors["light"])
    return (
        "display:flex;align-items:center;gap:10px;padding:12px 16px;"
        f"background-color:{colors['bg']};color:{colors['text']};"
        "border-radius:10px;margin-bottom:8px;"
    )


def valid_theme(value: str) -> bool:
    return value in _THEMES
