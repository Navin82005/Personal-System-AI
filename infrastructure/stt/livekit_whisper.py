import asyncio
from livekit import rtc
from livekit.agents import stt, utils
from livekit.agents.stt import SpeechEvent, SpeechEventType, SpeechData
from infrastructure.stt.whisper_service import WhisperService

class WhisperSTT(stt.STT):
    def __init__(self, model_size="tiny"):
        super().__init__(
            capabilities=stt.STTCapabilities(streaming=False, interim_results=False)
        )
        self._whisper = WhisperService(model_size=model_size)

    async def _recognize(
        self,
        *,
        buffer: utils.AudioBuffer,
        language: str | None = None,
    ) -> stt.SpeechEvent:
        # Convert LiveKit AudioFrames to bytes
        frames = utils.merge_frames(buffer)
        
        # We need a proper WAV structure for faster-whisper.
        import io
        import wave
        
        wav_io = io.BytesIO()
        with wave.open(wav_io, 'wb') as wav_file:
            wav_file.setnchannels(frames.num_channels)
            wav_file.setsampwidth(2) # 16-bit PCM
            wav_file.setframerate(frames.sample_rate)
            wav_file.writeframes(frames.data.tobytes())
            
        wav_io.seek(0)
        
        # run in thread pool
        text = await asyncio.to_thread(self._whisper.transcribe, wav_io.read())
        
        event = stt.SpeechEvent(
            type=stt.SpeechEventType.FINAL_TRANSCRIPT,
            alternatives=[stt.SpeechData(text=text, language=language or "en")]
        )
        return event
