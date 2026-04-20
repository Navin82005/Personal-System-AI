from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass

from config import settings
from utils.audio import chunk_pcm16, pcm16_frames_to_wav_bytes, resample_pcm16, rms_pcm16, wav_bytes_to_pcm16

logger = logging.getLogger("voice")


@dataclass(frozen=True)
class VoiceSessionConfig:
    room_name: str
    assistant_identity: str = "personal-ai"
    assistant_name: str = "Personal AI"
    # Voice activity detection (simple RMS threshold)
    vad_rms_threshold: int = 400
    vad_silence_ms: int = 900
    min_utterance_ms: int = 600
    # Output audio format for LiveKit publishing
    out_sample_rate: int = 48000
    out_channels: int = 1


class VoiceSessionService:
    """
    LiveKit-backed speech-to-speech agent:

    Remote user audio -> STT -> ResponseOrchestrator -> TTS -> publish audio.

    Also publishes JSON "events" over LiveKit data channel for:
    - status (listening/processing/speaking)
    - transcript updates
    - assistant text
    """

    def __init__(self, *, stt, tts, orchestrator):
        self.stt = stt
        self.tts = tts
        self.orchestrator = orchestrator
        self._stop = asyncio.Event()
        self._speaking_task: asyncio.Task | None = None
        self._speaking_cancel = asyncio.Event()

        try:
            from livekit import api, rtc  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "LiveKit Python RTC SDK is required for real-time voice sessions."
            ) from e

        self._api = api
        self._rtc = rtc
        self.room = rtc.Room()
        self._audio_source = rtc.AudioSource(sample_rate=48000, num_channels=1)
        self._local_track = rtc.LocalAudioTrack.create_audio_track("assistant-audio", self._audio_source)

    async def start_session(self, cfg: VoiceSessionConfig) -> None:
        token = self._mint_token(cfg.room_name, cfg.assistant_identity, cfg.assistant_name)
        await self.room.connect(settings.livekit_url, token)

        await self.room.local_participant.publish_track(self._local_track)
        self._publish_event({"type": "status", "status": "listening"})

        @self.room.on("track_subscribed")
        def _on_track_subscribed(track, publication, participant):  # noqa: ANN001
            # Ignore our own audio
            if participant.identity == cfg.assistant_identity:
                return
            if track.kind != self._rtc.TrackKind.KIND_AUDIO:
                return
            # Never let background task exceptions crash the process silently.
            asyncio.create_task(self._safe_process_audio_stream(track, participant, cfg))

        @self.room.on("disconnected")
        def _on_disconnected():  # noqa: ANN001
            self._stop.set()

        await self._stop.wait()
        try:
            await self.room.disconnect()
        except Exception:
            pass

    async def stop_session(self) -> None:
        self._stop.set()

    async def _safe_process_audio_stream(self, track, participant, cfg: VoiceSessionConfig) -> None:  # noqa: ANN001
        try:
            await self.process_audio_stream(track, participant, cfg)
        except Exception as e:
            logger.exception({"stage": "VOICE_STREAM_ERROR", "error": str(e)})
            self._publish_event({"type": "status", "status": "idle"})
            self._publish_event({"type": "error", "message": f"Voice pipeline error: {e}"})

    async def process_audio_stream(self, track, participant, cfg: VoiceSessionConfig) -> None:  # noqa: ANN001
        """
        Consume a subscribed LiveKit audio track and run simple VAD to segment utterances.
        """
        stream = self._rtc.AudioStream(track)

        pcm_buf = bytearray()
        voiced_ms = 0
        silence_ms = 0
        last_voice_t = time.time()

        def _get_attr(obj, *names):
            for n in names:
                if hasattr(obj, n):
                    return getattr(obj, n)
            return None

        def _extract_audio_frame(evt):
            # LiveKit AudioStream yields AudioFrameEvent in some SDK versions.
            f = _get_attr(evt, "frame") or evt

            raw = _get_attr(f, "data", "buffer", "samples")
            if raw is None:
                return None
            try:
                pcm = bytes(raw)
            except Exception:
                try:
                    # Some SDKs expose a memoryview-like object.
                    pcm = raw.tobytes()
                except Exception:
                    return None

            sample_rate = _get_attr(f, "sample_rate", "sampleRate") or _get_attr(evt, "sample_rate", "sampleRate")
            num_channels = _get_attr(f, "num_channels", "numChannels") or _get_attr(evt, "num_channels", "numChannels")
            samples_per_channel = _get_attr(f, "samples_per_channel", "samplesPerChannel") or _get_attr(
                evt, "samples_per_channel", "samplesPerChannel"
            )

            try:
                sr = int(sample_rate) if sample_rate is not None else 48000
            except Exception:
                sr = 48000
            try:
                ch = int(num_channels) if num_channels is not None else 1
            except Exception:
                ch = 1
            try:
                spc = int(samples_per_channel) if samples_per_channel is not None else max(1, (len(pcm) // 2) // max(ch, 1))
            except Exception:
                spc = max(1, (len(pcm) // 2) // max(ch, 1))

            return pcm, sr, ch, spc

        last_sr = 48000
        async for evt in stream:
            if self._stop.is_set():
                break

            extracted = _extract_audio_frame(evt)
            if not extracted:
                continue
            pcm, sr, ch, samples_per_channel = extracted
            last_sr = sr
            logger.debug(
                {
                    "stage": "AUDIO_CHUNK",
                    "bytes": len(pcm),
                    "sample_rate": sr,
                    "channels": ch,
                    "samples_per_channel": samples_per_channel,
                }
            )

            # Convert to mono for RMS/VAD.
            if ch > 1:
                try:
                    import audioop

                    pcm_mono = audioop.tomono(pcm, 2, 0.5, 0.5)
                except Exception:
                    pcm_mono = pcm
            else:
                pcm_mono = pcm

            energy = rms_pcm16(pcm_mono, 1)
            frame_ms = int(1000 * (samples_per_channel / max(sr, 1)))

            if energy >= cfg.vad_rms_threshold:
                pcm_buf.extend(pcm_mono)
                voiced_ms += frame_ms
                silence_ms = 0
                last_voice_t = time.time()
            else:
                if pcm_buf:
                    pcm_buf.extend(pcm_mono)
                silence_ms += frame_ms

            # Finalize utterance after enough silence.
            if pcm_buf and silence_ms >= cfg.vad_silence_ms and voiced_ms >= cfg.min_utterance_ms:
                utter_pcm = bytes(pcm_buf)
                pcm_buf.clear()
                voiced_ms = 0
                silence_ms = 0
                logger.info(
                    {
                        "stage": "UTTERANCE_FINALIZED",
                        "bytes": len(utter_pcm),
                        "sample_rate": sr,
                    }
                )
                await self._handle_utterance(utter_pcm, sr, cfg)

            # If user starts speaking while assistant is speaking, interrupt.
            if self._speaking_task and not self._speaking_task.done() and energy >= cfg.vad_rms_threshold:
                self._speaking_cancel.set()

        # Flush any remaining audio (best-effort)
        if pcm_buf and voiced_ms >= cfg.min_utterance_ms:
            await self._handle_utterance(bytes(pcm_buf), last_sr, cfg)

    async def transcribe_audio(self, wav_bytes: bytes) -> str:
        return await asyncio.to_thread(self.stt.transcribe, wav_bytes)

    async def generate_response(self, text: str) -> str:
        logger.info({"stage": "ORCHESTRATOR_INPUT", "text": text})
        res = await asyncio.to_thread(self.orchestrator.handle_user_query, text)
        logger.info({"stage": "ORCHESTRATOR_OUTPUT", "text": res.answer})
        return res.answer

    async def synthesize_speech(self, text: str) -> tuple[bytes, int]:
        # Coqui service exposes synthesize_pcm16; fall back to synthesize() if needed.
        if hasattr(self.tts, "synthesize_pcm16"):
            return await asyncio.to_thread(self.tts.synthesize_pcm16, text)
        wav_bytes = await asyncio.to_thread(self.tts.synthesize, text)
        pcm, sr, _ch = wav_bytes_to_pcm16(wav_bytes)
        # Wrap back to wav bytes so downstream is consistent
        return pcm16_frames_to_wav_bytes([pcm], sr, 1), sr

    async def stream_audio_output(self, wav_bytes: bytes, sr: int, cfg: VoiceSessionConfig) -> None:
        pcm, in_sr, ch = wav_bytes_to_pcm16(wav_bytes)
        if ch != 1:
            # Best-effort downmix.
            try:
                import audioop

                pcm = audioop.tomono(pcm, 2, 0.5, 0.5)
            except Exception:
                pass

        pcm = resample_pcm16(pcm, in_sr, cfg.out_sample_rate, 1)

        # 20ms frames @ 48kHz => 960 samples
        frame_samples = int(cfg.out_sample_rate * 0.02)
        for chunk in chunk_pcm16(pcm, frame_samples=frame_samples, channels=1):
            if self._stop.is_set() or self._speaking_cancel.is_set():
                break
            samples = max(1, len(chunk) // 2)  # mono PCM16
            audio_frame = self._rtc.AudioFrame(
                data=chunk,
                sample_rate=cfg.out_sample_rate,
                num_channels=1,
                samples_per_channel=samples,
            )
            await self._audio_source.capture_frame(audio_frame)

    async def _handle_utterance(self, pcm: bytes, sr: int, cfg: VoiceSessionConfig) -> None:
        self._publish_event({"type": "status", "status": "processing"})

        wav_bytes = pcm16_frames_to_wav_bytes([pcm], sr, 1)
        transcript = (await self.transcribe_audio(wav_bytes)).strip()
        if not transcript:
            self._publish_event({"type": "status", "status": "listening"})
            return

        self._publish_event({"type": "transcript", "text": transcript, "is_final": True})

        answer = await self.generate_response(transcript)
        self._publish_event({"type": "assistant_text", "text": answer})

        self._publish_event({"type": "status", "status": "speaking"})
        self._speaking_cancel.clear()

        async def speak():
            wav_out, out_sr = await self.synthesize_speech(answer)
            await self.stream_audio_output(wav_out, out_sr, cfg)

        self._speaking_task = asyncio.create_task(speak())
        try:
            await self._speaking_task
        except Exception:
            pass
        finally:
            self._publish_event({"type": "status", "status": "listening"})

    def _publish_event(self, payload: dict) -> None:
        try:
            data = json.dumps(payload).encode("utf-8")
            self.room.local_participant.publish_data(data, kind=self._rtc.DataPacketKind.RELIABLE)
        except Exception:
            pass

    def _mint_token(self, room_name: str, identity: str, name: str) -> str:
        api_key = settings.livekit_api_key
        api_secret = settings.livekit_api_secret
        if not api_key or not api_secret:
            raise RuntimeError("LIVEKIT_API_KEY and LIVEKIT_API_SECRET are required")
        grant = self._api.VideoGrants(room_join=True, room=room_name)
        tok = self._api.AccessToken(api_key, api_secret).with_identity(identity).with_name(name).with_grants(grant)
        return tok.to_jwt()
