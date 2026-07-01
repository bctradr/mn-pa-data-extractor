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

    /* Tighten top padding app-wide */
    .block-container { padding-top: 1.5rem !important; }
    /* Tighten gaps between widget rows */
    div[data-testid="stVerticalBlock"] { gap: 0.4rem; }

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

    /* Variant for use above content that isn't a bordered container
       (e.g., above a st.dataframe). No negative margin so the table
       below isn't pulled up into the bar. */
    .softpro-section-bar {
        background: #0f3a5f;
        color: white;
        font-size: 0.9rem;
        font-weight: 600;
        padding: 8px 14px;
        border-radius: 4px;
        margin: 0.6rem 0 0.4rem 0;
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

    /* File uploader — bigger, more obvious drop zone with custom text.
       Streamlit renders "Drag and drop file here" + size info internally;
       we hide its small block and inject our own larger styled label. */
    div[data-testid="stFileUploader"] section {
        background-color: #f0f4f8 !important;
        border: 2px dashed #1a4e7a !important;
        border-radius: 6px !important;
        padding: 24px !important;
        min-height: 90px !important;
        position: relative;
    }
    /* Hide Streamlit's default tiny label block */
    div[data-testid="stFileUploader"] section > div:first-child {
        visibility: hidden;
        position: absolute;
        height: 0;
    }
    /* Inject our larger custom label */
    div[data-testid="stFileUploader"] section::before {
        content: "📂 Drag and Drop Here  •  200MB per file  •  PDF, DOCX, MSG, EML";
        display: block;
        text-align: center;
        font-size: 0.95rem;
        font-weight: 500;
        color: #1a4e7a;
        margin-bottom: 10px;
    }
    /* Center the Browse button below the label */
    div[data-testid="stFileUploader"] section > button,
    div[data-testid="stFileUploader"] section > [data-testid="stFileUploaderDropzone"] button {
        margin: 0 auto;
        display: block;
    }

    /* ── Buttons ──────────────────────────────────────────── */
    button[kind="primary"], .stButton > button[kind="primary"] {
        background-color: #0f3a5f !important;
        border-color: #0f3a5f !important;
        color: white !important;
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

    /* ── Order Queue table ────────────────────────────────── */
    /* Note: st.dataframe headers are rendered to <canvas> by Glide Data
       Grid, so they cannot be styled with CSS. The Order Queue page adds
       a colored title bar ABOVE the table instead. */
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
    st.container(border=True) block — the bar visually attaches to it)."""
    st.markdown(
        f'<div class="softpro-section-header">{title}</div>',
        unsafe_allow_html=True,
    )


def section_bar(title: str):
    """Standalone blue section bar — for use above content that isn't
    a bordered container (e.g., above a st.dataframe)."""
    st.markdown(
        f'<div class="softpro-section-bar">{title}</div>',
        unsafe_allow_html=True,
    )
