import io
import os
from faster_whisper import WhisperModel
from domain.interfaces.stt_interface import STTService

class WhisperService(STTService):
    def __init__(self, model_size="tiny"):
        # "tiny", "base", "small", "medium", "large" 
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")

    def transcribe(self, audio_bytes: bytes) -> str:
        """Transcribe audio bytes to text using faster-whisper."""
        # Using a temporary file or BytesIO buffer. faster-whisper accepts BinaryIO
        audio_stream = io.BytesIO(audio_bytes)
        # Note: faster_whisper expects the audio format to be somewhat standard (e.g., wav, mp3, flac)
        segments, info = self.model.transcribe(audio_stream, beam_size=5)
        text = " ".join([segment.text for segment in segments])
        return text.strip()
