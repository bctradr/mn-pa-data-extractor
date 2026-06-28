"""
3_PA_Extractor.py
MN Purchase Agreement Extractor with pluggable model backend (GLM-5.2 default).
"""

import streamlit as st
import base64
import json
import pandas as pd
from io import BytesIO
import zipfile

from ui_theme import apply_theme, section_header, section_bar
from summary_generator import generate_text_summary, generate_html_summary
from models.base import ModelBackend
import config
from extraction_prompt import EXTRACTION_SYSTEM_PROMPT
from extractor import flatten_for_csv, parse_currency
from supabase_client import set_order_status, update_extraction

# Pluggable backend
def get_model_backend(model_choice):
    cfg = config.MODEL_CONFIG.get(model_choice, config.MODEL_CONFIG["glm"])
    if cfg["provider"] == "openrouter":
        from models.glm_client import GLMClient
        return GLMClient(cfg["api_key"])
    elif cfg["provider"] == "anthropic":
        import anthropic
        client = anthropic.Anthropic(api_key=cfg["api_key"])
        class AnthropicBackend(ModelBackend):
            def extract(self, pdf_files):
                content = []
                for pdf_bytes, filename in pdf_files:
                    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")
                    content.append({
                        "type": "document",
                        "source": {"type": "base64", "media_type": "application/pdf", "data": pdf_b64}
                    })
               