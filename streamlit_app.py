"""
streamlit_app.py
════════════════
Entry point for the multi-page Streamlit app. Pages live in the pages/
folder and appear in the sidebar nav.
"""

import streamlit as st
from ui_theme import apply_theme


st.set_page_config(
    page_title="MN PA Tools",
    page_icon="🏠",
    layout="wide",
)

apply_theme()


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
