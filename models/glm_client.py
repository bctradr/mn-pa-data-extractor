import openai
from models.base import ModelBackend
from typing import Dict, Any

class GLMClient(ModelBackend):
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        self.model = "z-ai/glm-5.2"

    def extract(self, pdf_text: str, schema: Dict) -> Dict:
        # TODO: Integrate your full extraction_prompt.py logic here for best results
        # For now, a basic structured call
        prompt = f"""Extract structured data from this Minnesota Purchase Agreement using the following schema: {schema}

Document text:
{pdf_text[:20000]}  # Limit for safety
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=4000,
        )
        return {
            "raw_response": response.choices[0].message.content,
            "model": "glm-5.2",
            "usage": response.usage if hasattr(response, 'usage') else None
        }

    def get_model_name(self) -> str:
        return "GLM-5.2 (OpenRouter)"