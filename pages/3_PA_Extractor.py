"""
3_PA_Extractor.py
Standalone PA Extractor page with pluggable model backend.
"""

import streamlit as st
import base64
import json
import pandas as pd
from datetime import datetime
from io import BytesIO
import zipfile

from ui_theme import apply_theme, section_header
from summary_generator import generate_text_summary, generate_html_summary
from extractor import flatten_for_csv, parse_currency  # Keep your helpers
from models.base import ModelBackend
import config

# Import your prompt and schema
from extraction_prompt import EXTRACTION_SYSTEM_PROMPT
# from extraction_schema.json import load_schema  # Adjust if needed

st.set_page_config(page_title="PA Extractor", page_icon="📄", layout="wide")
apply_theme()

# Global model selector (already in main app, but fallback)
if "model_choice" not in st.session_state:
    st.session_state.model_choice = config.DEFAULT_MODEL

model_choice = st.session_state.model_choice

st.title("📄 PA Extractor")
st.caption(f"Using: **{config.MODEL_CONFIG[model_choice]['name']}**")

# ── Upload ───────────────────────────────────────────
uploaded_file = st.file_uploader(
    "Purchase Agreement (PDF)",
    type=["pdf"],
    accept_multiple_files=True,
    help="Upload one or more PDFs — all from the same transaction",
)

if not uploaded_file:
    st.info("👈 Upload PDFs to get started.")
    st.stop()

if st.button("🔍 Extract Fields", type="primary", use_container_width=True):
    with st.spinner(f"Extracting with {config.MODEL_CONFIG[model_choice]['name']}..."):
        try:
            pdf_files = [(f.read(), f.name) for f in uploaded_file]
            
            # Use the pluggable backend
            from models.base import ModelBackend
            
            def get_backend(choice):
                cfg = config.MODEL_CONFIG.get(choice, config.MODEL_CONFIG["glm"])
                if cfg["provider"] == "openrouter":
                    from models.glm_client import GLMClient
                    return GLMClient(cfg["api_key"])
                elif cfg["provider"] == "anthropic":
                    # Your original Anthropic logic
                    import anthropic
                    client = anthropic.Anthropic(api_key=cfg["api_key"])
                    class AnthropicBackend(ModelBackend):
                        def extract(self, pdf_text: str, schema: dict) -> dict:
                            # Reuse your original extraction logic here
                            content = []
                            for pdf_bytes, filename in pdf_files:
                                pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")