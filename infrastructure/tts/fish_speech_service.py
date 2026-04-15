import os
import requests
from domain.interfaces.tts_interface import TTSService


class FishSpeechService(TTSService):
    def __init__(self, api_key: str = None, api_url: str = "https://api.assemblyai.com/v2/transcript"):
        # Load from env if not provided
        self.api_key = api_key or os.getenv("ASSEMBLYAI_API_KEY", "")
        self.api_url = api_url

    def synthesize(self, text: str) -> bytes:
        """Synthesize text to audio using Fish Audio API."""
        if not self.api_key:
            print("Warning: FISH_AUDIO_API_KEY not set. Returning a mock empty audio payload.")
            # For development, just return dummy bytes or raise an error
            return b""
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Typical Fish Audio v1 API structure
        payload = {
            "text": text,
            # we can specify reference_id for a specific voice model if needed
        }
        
        try:
            response = requests.post(self.api_url, json=payload, headers=headers)
            response.raise_for_status()
            return response.content
        except Exception as e:
            print(f"Error in TTS synthesis: {e}")
            return b""
