"""
streamlit_app.py
Entry point for the multi-page Streamlit app.
"""

import streamlit as st
from ui_theme import apply_theme
import config

st.set_page_config(
    page_title="MN PA Tools",
    page_icon="🏠",
    layout="wide",
)

apply_theme()

st.title("🏠 MN Purchase Agreement Tools")
st.caption("Pick a workflow from the sidebar.")

# Global model selector
model_choice = st.selectbox(
    "🤖 Select AI Model (GLM-5.2 is default & much cheaper)",
    options=["glm", "claude"],
    format_func=lambda x: config.MODEL_CONFIG[x]["name"],
    index=0,
    help="GLM-5.2 via OpenRouter is recommended"
)

if "model_choice" not in st.session_state or st.session_state.model_choice != model_choice:
    st.session_state.model_choice = model_choice

st.markdown("""
### Workflows

**📝 New Order**  
Upload purchase agreement and supporting documents, fill intake fields, save to queue.

**📋 Order Queue**  
View saved orders. Run extractor, review, export.

**📄 PA Extractor**  
Standalone extractor — upload PA/addenda, extract, review, export.
""")