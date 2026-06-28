from abc import ABC, abstractmethod
from typing import Dict, Any

class ModelBackend(ABC):
    @abstractmethod
    def extract(self, pdf_text: str, schema: Dict) -> Dict:
        """Extract structured data from PDF text using the model."""
        pass

    def get_model_name(self) -> str:
        return "Unknown Model"