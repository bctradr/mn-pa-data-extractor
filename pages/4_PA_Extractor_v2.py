"""
4_PA_Extractor_v2.py
Alternate view of the PA Extractor with pluggable model backend.
"""

import streamlit as st
import json
import pandas as pd
import zipfile
from io import BytesIO

from ui_theme import apply_theme
from summary_generator import generate_text_summary, generate_html_summary
from models.base import ModelBackend
import config
from extraction_prompt import EXTRACTION_SYSTEM_PROMPT
from supabase_client import set_order_status, update_extraction
from extractor import flatten_combined_for_csv, intake_summary_text, parse_currency

st.set_page_config(page_title="PA Extractor v2", page_icon="📑", layout="wide")
apply_theme()

st.title("📑 PA Extractor v2")
st.caption(f"Using: **{config.MODEL_CONFIG[st.session_state.get('model_choice', config.DEFAULT_MODEL)]['name']}**")

# Model selector
if "model_choice" not in st.session_state:
    st.session_state.model_choice = config.DEFAULT_MODEL

# Review mode detection
review_order = st.session_state.get("review_order")
review_order_id = st.session_state.get("review_order_id")
review_files = st.session_state.get("review_files")
in_review_mode = bool(review_order and review_files)

# Upload / Extract
with st.sidebar:
    st.header("Upload")
    if in_review_mode:
        st.info(f"Reviewing order with {len(review_files)} files.")
        uploaded_file = None
    else:
        uploaded_file = st.file_uploader("Purchase Agreement PDF(s)", type=["pdf"], accept_multiple_files=True)
        if uploaded_file:
            st.success(f"Loaded {len(uploaded_file)} file(s)")

if in_review_mode or uploaded_file:
    if st.button("🔍 Extract Fields", type="primary"):
        with st.spinner(f"Extracting with {config.MODEL_CONFIG[st.session_state.model_choice]['name']}..."):
            try:
                pdf_files = [(f.read(), f.name) for f in (review_files or uploaded_file)]
                # Placeholder - replace with your full extraction call
                st.success("Extraction complete!")
                st.json({"model": config.MODEL_CONFIG[st.session_state.model_choice]["name"], "status": "success"})
            except Exception as e:
                st.error(f"Extraction failed: {e}")

st.info("Full extraction integration coming in next update. Test the dropdown and button first.")