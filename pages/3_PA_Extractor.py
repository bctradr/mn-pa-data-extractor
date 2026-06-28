import streamlit as st
import base64
import json
import pandas as pd
from io import BytesIO
import zipfile

from ui_theme import apply_theme
from summary_generator import generate_text_summary, generate_html_summary
from models.base import ModelBackend
import config

st.set_page_config(page_title="PA Extractor", page_icon="📄", layout="wide")
apply_theme()

st.title("📄 PA Extractor")
st.caption(f"Using: **{config.MODEL_CONFIG[st.session_state.get('model_choice', config.DEFAULT_MODEL)]['name']}**")

# Upload
uploaded_file = st.file_uploader("Upload Purchase Agreement PDF(s)", type=["pdf"], accept_multiple_files=True)

if uploaded_file and st.button("Extract with Selected Model", type="primary"):
    with st.spinner("Extracting..."):
        try:
            # Simple test call - replace with your full logic
            st.success("Extraction logic placeholder - GLM-5.2 ready!")
            st.json({"status": "success", "model": config.MODEL_CONFIG[st.session_state.get('model_choice', 'glm')]["name"]})
        except Exception as e:
            st.error(f"Error: {e}")

st.info("Full integration coming in next update. Test the dropdown first.")