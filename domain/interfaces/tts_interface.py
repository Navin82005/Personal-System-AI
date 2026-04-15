from abc import ABC, abstractmethod

class TTSService(ABC):
    @abstractmethod
    def synthesize(self, text: str) -> bytes:
        """Synthesize text to audio bytes."""
        pass
