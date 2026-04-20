from __future__ import annotations

import audioop
import io
import wave
from typing import Iterable, Iterator, Tuple


def pcm16_frames_to_wav_bytes(frames: Iterable[bytes], sample_rate: int, channels: int) -> bytes:
    """
    Wrap raw little-endian PCM16 frames into a WAV container (in-memory).
    """
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # PCM16
        wf.setframerate(sample_rate)
        for f in frames:
            wf.writeframes(f)
    return buf.getvalue()
    

def wav_bytes_to_pcm16(wav_bytes: bytes) -> Tuple[bytes, int, int]:
    """
    Decode a WAV container to PCM16 bytes.
    """
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        channels = wf.getnchannels()
        sample_rate = wf.getframerate()
        sampwidth = wf.getsampwidth()
        if sampwidth != 2:
            # Convert to 16-bit if needed
            raw = wf.readframes(wf.getnframes())
            raw_16 = audioop.lin2lin(raw, sampwidth, 2)
            return raw_16, sample_rate, channels
        raw = wf.readframes(wf.getnframes())
        return raw, sample_rate, channels


def resample_pcm16(pcm: bytes, src_rate: int, dst_rate: int, channels: int) -> bytes:
    if src_rate == dst_rate:
        return pcm
    # audioop.ratecv works on mono/stereo interleaved PCM.
    converted, _state = audioop.ratecv(pcm, 2, channels, src_rate, dst_rate, None)
    return converted


def chunk_pcm16(pcm: bytes, *, frame_samples: int, channels: int) -> Iterator[bytes]:
    """
    Yield PCM16 frames in chunks of `frame_samples` samples per channel.
    """
    bytes_per_sample = 2
    frame_bytes = frame_samples * channels * bytes_per_sample
    for i in range(0, len(pcm), frame_bytes):
        yield pcm[i : i + frame_bytes]


def rms_pcm16(pcm_frame: bytes, channels: int) -> int:
    """
    Root-mean-square energy for a PCM16 frame.
    """
    if not pcm_frame:
        return 0
    return audioop.rms(pcm_frame, 2)

