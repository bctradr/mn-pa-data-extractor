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

# Model selector (if not already in main app)
if "model_choice" not in st.session_state:
    st.session_state.model_choice = config.DEFAULT_MODEL

# Review mode detection (keep your existing logic)
review_order = st.session_state.get("review_order")
review_order_id = st.session_state.get("review_order_id")
review_files = st.session_state.get("review_files")
in_review_mode = bool(review_order and review_files)

# Your existing banner, upload, etc. code goes here...
# (I kept the structure the same for minimal disruption)

# ── Extraction Function with Pluggable Backend ─────
def extract_from_pdf(pdf_files):
    """Use the selected model backend."""
    backend = get_model_backend(st.session_state.model_choice)
    # Convert PDFs to text or pass directly (adapt for GLM