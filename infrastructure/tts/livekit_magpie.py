import os
import io
import wave
import asyncio
import aiohttp
from livekit import rtc
from livekit.agents import tts
from config import settings

class MagpieChunkedStream(tts.ChunkedStream):
    def __init__(self, text: str, api_key: str, prompt_file: str):
        super().__init__()
        self._text = text
        self._api_key = api_key
        self._prompt_file = prompt_file

    async def _main_task(self):
        # We perform the API request and yield the AudioFrame
        url = os.getenv("NVIDIA_NIM_URL", "https://api.nvidia.com/v1/audio/synthesize")
        
        form_data = aiohttp.FormData()
        form_data.add_field('language', 'en-US')
        form_data.add_field('text', self._text)
        
        # Load the prompt file
        try:
            with open(self._prompt_file, 'rb') as f:
                prompt_data = f.read()
            form_data.add_field('audio_prompt', prompt_data, filename='prompt.wav', content_type='audio/wav')
        except FileNotFoundError:
            raise FileNotFoundError(f"Audio prompt file {self._prompt_file} not found. Magpie Zero-shot requires this.")
        
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "audio/wav"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=form_data, headers=headers) as resp:
                if resp.status != 200:
                    err_text = await resp.text()
                    raise Exception(f"Magpie TTS API error: {resp.status} - {err_text}")
                
                audio_bytes = await resp.read()
                
                # Parse WAV
                wav_io = io.BytesIO(audio_bytes)
                with wave.open(wav_io, 'rb') as w:
                    framerate = w.getframerate()
                    channels = w.getnchannels()
                    nframes = w.getnframes()
                    pcm_data = w.readframes(nframes)
                    
                    # Create LiveKit rtc.AudioFrame
                    frame = rtc.AudioFrame(pcm_data, framerate, channels, nframes)
                    
                    self._event_ch.send_nowait(
                        tts.SynthesizedAudio(
                            request_id=self._text, # simple id mapping
                            frame=frame
                        )
                    )


class MagpieTTS(tts.TTS):
    def __init__(self, prompt_file="prompt.wav"):
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False)
        )
        self.api_key = settings.nvidia_api_key
        self.prompt_file = prompt_file
        
    def synthesize(self, text: str) -> "tts.ChunkedStream":
        return MagpieChunkedStream(text, getattr(self, "api_key", ""), self.prompt_file)

