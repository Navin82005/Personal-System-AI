from __future__ import annotations

import io
import wave

import numpy as np

from domain.interfaces.tts_interface import TTSService


class CoquiTTSService(TTSService):
    """
    Coqui TTS (local) implementation.

    Note: Coqui TTS model download can be large; ensure models are available in the runtime environment.
    """

    def __init__(self, model_name: str = "tts_models/en/vctk/vits", speaker: str | None = None, gpu: bool = False):
        try:
            from TTS.api import TTS  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "Coqui TTS is not installed. Install `TTS` (Coqui) and its deps to enable voice."
            ) from e

        self.tts = TTS(model_name=model_name, progress_bar=False, gpu=gpu)
        self.speaker = speaker
        # Best-effort; different models expose this differently.
        self.sample_rate = getattr(getattr(self.tts, "synthesizer", None), "output_sample_rate", 22050)

    def synthesize(self, text: str) -> bytes:
        wav, sr = self.synthesize_pcm16(text)
        return wav

    def synthesize_pcm16(self, text: str) -> tuple[bytes, int]:
        """
        Returns (wav_bytes, sample_rate).
        """
        if self.speaker:
            audio = self.tts.tts(text=text, speaker=self.speaker)
        else:
            audio = self.tts.tts(text=text)

        # audio is a float32 numpy array in [-1, 1]
        audio_np = np.array(audio, dtype=np.float32)
        audio_np = np.clip(audio_np, -1.0, 1.0)
        pcm16 = (audio_np * 32767.0).astype(np.int16).tobytes()

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(int(self.sample_rate))
            wf.writeframes(pcm16)

        return buf.getvalue(), int(self.sample_rate)

