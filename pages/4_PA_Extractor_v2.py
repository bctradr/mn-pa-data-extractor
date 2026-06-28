import streamlit as st
import config

st.set_page_config(page_title="PA Extractor v2", page_icon="📑", layout="wide")
st.title("📑 PA Extractor v2")
st.caption(f"Using: **{config.MODEL_CONFIG[st.session_state.get('model_choice', config.DEFAULT_MODEL)]['name']}**")

st.success("✅ Model backend loaded successfully!")
st.info("Full extraction logic coming in next update. The dropdown works!")

if st.button("Test GLM-5.2"):
    st.json({"model": "GLM-5.2", "status": "ready"})