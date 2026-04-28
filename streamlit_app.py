"""
streamlit_app.py
════════════════
Entry point for the multi-page Streamlit app. The actual workflows live in
the pages/ folder and appear in the sidebar nav.

This file is what Streamlit Community Cloud points to as the main file —
update the deployment's "Main file path" from app.py to streamlit_app.py.
"""

import streamlit as st


st.set_page_config(
    page_title="MN PA Tools",
    page_icon="🏠",
    layout="wide",
)


# ── Theme CSS shared across all pages ────────────────
st.markdown("""
<style>
    header[data-testid="stHeader"] { background-color: #1a4e7a; }
    h1 { color: #1a4e7a !important; }
    h2, h3 { color: #2a6496 !important; }
    button[data-baseweb="tab"] { color: #1a4e7a !important; font-weight: 500; }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #1a4e7a !important;
        border-bottom-color: #1a4e7a !important;
    }
    button[kind="primary"], .stButton > button[kind="primary"] {
        background-color: #1a4e7a !important;
        border-color: #1a4e7a !important;
    }
    div[data-testid="stAlert"] { border-left-color: #1a4e7a; }
    section[data-testid="stSidebar"] { background-color: #e8f0f8; }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2 { color: #1a4e7a !important; }
</style>
""", unsafe_allow_html=True)


st.title("🏠 MN Purchase Agreement Tools")
st.caption("Pick a workflow from the sidebar.")

st.markdown("""
### Workflows

**📝 New Order**
Opens a new order: upload the purchase agreement and supporting documents,
fill in intake fields (closer, lender, mortgage broker, etc.), and save it
to the queue.

**📋 Order Queue**
View all saved orders. Run the PA extractor on any order with one click,
review extracted fields alongside intake info, and export a unified
intake + extracted-data file in text, HTML, CSV, or JSON for TPS upload.

**📄 PA Extractor**
Standalone PA extractor — upload a PA and any addenda directly, extract
fields, review, and export. For one-off extractions that don't go through
the queue.
""")
