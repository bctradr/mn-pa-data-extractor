"""
ui_theme.py
═══════════
Shared SoftPro-style CSS injected by every page. Each page calls
apply_theme() at the top to get consistent styling.

Streamlit's CSS doesn't automatically propagate from the entry-point
streamlit_app.py to pages/, so the shared block lives here.
"""

import streamlit as st


def apply_theme():
    """Inject SoftPro-style CSS. Call once at the top of each page."""
    st.markdown("""
<style>
    /* ── App chrome ──────────────────────────────────────── */
    header[data-testid="stHeader"] { background-color: #0f3a5f; }
    h1 { color: #0f3a5f !important; }
    h2, h3 { color: #1a4e7a !important; }

    /* ── Streamlit's native bordered container ────────────── */
    /* Used by st.container(border=True) on the New Order page. */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: #c8d4e0 !important;
        border-radius: 0 4px 4px 4px !important;
        background: #fafcfe;
    }

    /* ── SoftPro-style blue section header ────────────────── */
    .softpro-section-header {
        background: #0f3a5f;
        color: white;
        font-size: 0.85rem;
        font-weight: 600;
        padding: 6px 12px;
        border-radius: 4px 4px 0 0;
        margin-top: 0.6rem;
        margin-bottom: -8px;
        position: relative;
        z-index: 1;
    }

    /* ── Form inputs — SoftPro-style boxes ────────────────── */
    /* Text inputs and number inputs */
    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input {
        background-color: #f0f4f8 !important;
        border: 1px solid #c8d4e0 !important;
        border-radius: 3px !important;
        padding: 6px 10px !important;
    }
    div[data-testid="stTextInput"] input:focus,
    div[data-testid="stNumberInput"] input:focus {
        border-color: #1a4e7a !important;
        box-shadow: 0 0 0 1px #1a4e7a !important;
    }

    /* Selectboxes */
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
        background-color: #f0f4f8 !important;
        border: 1px solid #c8d4e0 !important;
        border-radius: 3px !important;
    }

    /* Text areas */
    div[data-testid="stTextArea"] textarea {
        background-color: #f0f4f8 !important;
        border: 1px solid #c8d4e0 !important;
        border-radius: 3px !important;
    }
    div[data-testid="stTextArea"] textarea:focus {
        border-color: #1a4e7a !important;
        box-shadow: 0 0 0 1px #1a4e7a !important;
    }

    /* Date inputs */
    div[data-testid="stDateInput"] input {
        background-color: #f0f4f8 !important;
        border: 1px solid #c8d4e0 !important;
        border-radius: 3px !important;
    }

    /* File uploader */
    div[data-testid="stFileUploader"] section {
        background-color: #f0f4f8 !important;
        border: 1px dashed #c8d4e0 !important;
        border-radius: 3px !important;
    }

    /* ── Buttons ──────────────────────────────────────────── */
    button[kind="primary"], .stButton > button[kind="primary"] {
        background-color: #0f3a5f !important;
        border-color: #0f3a5f !important;
    }

    /* ── Tabs (used heavily in PA Extractor) ──────────────── */
    button[data-baseweb="tab"] { color: #1a4e7a !important; font-weight: 500; }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #0f3a5f !important;
        border-bottom-color: #0f3a5f !important;
    }

    /* ── Alerts ───────────────────────────────────────────── */
    div[data-testid="stAlert"] { border-left-color: #0f3a5f; }

    /* ── Sidebar ──────────────────────────────────────────── */
    section[data-testid="stSidebar"] { background-color: #dde8f4; }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2 { color: #0f3a5f !important; }

    /* ── Order Queue table — blue header row ──────────────── */
    /* Targets the native st.dataframe header. Streamlit uses Glide
       Data Grid internally — these selectors may need adjustment if
       Streamlit upgrades. */
    div[data-testid="stDataFrame"] [role="columnheader"] {
        background-color: #0f3a5f !important;
        color: white !important;
        font-weight: 600 !important;
    }
    div[data-testid="stDataFrame"] [role="columnheader"] * {
        color: white !important;
    }
    /* Hide the column-header three-dot menu (sort still works via click) */
    div[data-testid="stDataFrame"] [data-testid="stDataFrameHeaderCellMenu"] {
        display: none !important;
    }
    div[data-testid="stDataFrame"] button[aria-label*="menu"] {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)


def section_header(title: str):
    """Render a SoftPro-style blue header bar (use just before a 
    st.container(border=True) block)."""
    st.markdown(
        f'<div class="softpro-section-header">{title}</div>',
        unsafe_allow_html=True,
    )
