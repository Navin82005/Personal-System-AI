from abc import ABC, abstractmethod
from typing import List, Dict, Any

class VectorStoreInterface(ABC):
    @abstractmethod
    def search(self, query: str, top_k: int = 5, where: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Search vector store for relevant chunks."""
        pass
