import os

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

DEFAULT_MODEL = "glm"

MODEL_CONFIG = {
    "glm": {
        "name": "GLM-5.2 (OpenRouter)",
        "provider": "openrouter",
        "model_id": "z-ai/glm-5.2",
        "api_key": OPENROUTER_API_KEY,
        "base_url": "https://openrouter.ai/api/v1",
    },
    "claude": {
        "name": "Claude (Anthropic)",
        "provider": "anthropic",
        "model_id": "claude-3-5-sonnet-20240620",
        "api_key": ANTHROPIC_API_KEY,
    }
}