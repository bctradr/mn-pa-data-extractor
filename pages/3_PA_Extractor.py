"""
3_PA_Extractor.py
MN Purchase Agreement Extractor with pluggable model backend.
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
from supabase_client import set_order_status, update_extraction  # Keep if used

# Pluggable backend helper
def get_model_backend(model_choice: str):
    cfg = config.MODEL_CONFIG.get(model_choice, config.MODEL_CONFIG["glm"])
    if cfg["provider"] == "openrouter":
        from models.glm_client import GLMClient
        return GLMClient(cfg["api_key"])
    elif cfg["provider"] == "anthropic":
        import anthropic
        client = anthropic.Anthropic(api_key=cfg["api_key"])
        class AnthropicBackend(ModelBackend):
            def extract(self, pdf_files: list) -> dict:
                content = []
                for pdf_bytes, filename in pdf_files:
                    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")
                    content.append({
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_b64,
                        },
                    })
                content.append({
                    "type": "text",
                    "text": "Extract all fields from this Minnesota purchase agreement. Return only JSON.",
                })
                response = client.messages.create(
                    model=cfg["model_id"],
                    max_tokens=4096,
                    temperature=0,
                    system=EXTRACTION_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": content}],
                )
                raw_text = response.content[0].text
                raw_text = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                return json.loads(raw_text)
            def get_model_name(self) -> str:
                return "Claude"
        return AnthropicBackend()
    raise ValueError("Unknown model")

# Rest of your UI code (unchanged except extraction call)
# ... (paste the rest of your original file here, replacing the extract_from_pdf call with the new backend)

st.title("🏠 MN Purchase Agreement Extractor")
st.caption(f"Using: **{config.MODEL_CONFIG[st.session_state.get('model_choice', config.DEFAULT_MODEL)]['name']}**")

# Upload and button code (keep your original)
# ...

# When extracting:
if st.button("🔍 Extract Fields"):
    with st.spinner("Extracting..."):
        pdf_files = [(f.read(), f.name) for f in uploaded_file]
        backend = get_model_backend(st.session_state.model_choice)
        result = backend.extract(pdf_files)
        st.session_state["extraction"] = result
        st.success(f"Used {backend.get_model_name()}")