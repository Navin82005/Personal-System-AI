from domain.interfaces.stt_interface import STTService
from domain.interfaces.tts_interface import TTSService
from application.use_cases.query_rag import RagPipeline
import logging

logger = logging.getLogger("livekit-agent-voice-query")

class VoiceQueryUseCase:
    def __init__(self, stt: STTService, tts: TTSService, rag: RagPipeline):
        self.stt = stt
        self.tts = tts
        self.rag = rag

    def execute(self, audio_bytes: bytes) -> dict:
        """
        Executes the full voice query pipeline: STT -> RAG -> TTS.
        """
        text = self.stt.transcribe(audio_bytes)
        
        logger.debug("User message transcribed message:", text)
        
        # If transcription is empty, return early
        if not text or not text.strip():
            return {
                "query": "",
                "answer": "I did not catch that.",
                "audio": self.tts.synthesize("I did not catch that.")
            }
        
        answer = self.rag.run(text)
        audio = self.tts.synthesize(answer)

        return {
            "query": text,
            "answer": answer,
            "audio": audio
        }
