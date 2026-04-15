from abc import ABC, abstractmethod
from typing import Dict, Any

class LLMInterface(ABC):
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate response given a prompt."""
        pass
