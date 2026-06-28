import streamlit as st
from models.base import ModelBackend
import config
from extraction_prompt import get_extraction_prompt  # Assuming you have this
from extraction_schema.json import load_schema  # Adjust if needed

def get_model_backend(model_choice: str = config.DEFAULT_MODEL) -> ModelBackend:
    """Return the correct backend based on selection."""
    cfg = config.MODEL_CONFIG.get(model_choice, config.MODEL_CONFIG["glm"])
    
    if cfg["provider"] == "openrouter":
        from models.glm_client import GLMClient
        return GLMClient(cfg["api_key"])
    elif cfg["provider"] == "anthropic":
        # Your existing Anthropic client logic here
        # Paste your current Anthropic extraction code
        from anthropic import Anthropic
        client = Anthropic(api_key=cfg["api_key"])
        # ... (keep your current extraction method)
        class AnthropicBackend(ModelBackend):
            def extract(self, pdf_text: str, schema: Dict) -> Dict:
                # Your existing extraction code
                pass
            def get_model_name(self) -> str:
                return "Claude"
        return AnthropicBackend()
    raise ValueError(f"Unknown provider: {cfg['provider']}")

# Main extraction function (update your existing one)
def extract_purchase_agreement(pdf_text: str, model_choice: str = config.DEFAULT_MODEL):
    backend = get_model_backend(model_choice)
    schema = load_schema()  # Your schema
    result = backend.extract(pdf_text, schema)
    st.info(f"Used model: {backend.get_model_name()}")
    return result