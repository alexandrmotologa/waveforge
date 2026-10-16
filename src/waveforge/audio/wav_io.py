"""High-fidelity WAV audio encoding and decoding."""

from __future__ import annotations
import io
import wave
import struct
import numpy as np
from typing import Tuple


def write_wav(
    filepath_or_buffer: str | io.BytesIO,
    left: np.ndarray,
    right: Optional[np.ndarray] = None,
    sample_rate: int = 44100,
    bit_depth: int = 16,
) -> None:
    """Encode audio channels into standard RIFF WAV format.

    Args:
        filepath_or_buffer: File path string or in-memory BytesIO stream.
        left: Left channel float array [-1.0, 1.0].
        right: Optional Right channel float array [-1.0, 1.0] (mono if None).
        sample_rate: Sampling frequency in Hz.
        bit_depth: 16 (signed integer) or 32 (float or int32).
    """
    is_stereo = right is not None
    num_channels = 2 if is_stereo else 1

    n_samples = len(left)
    left_clamped = np.clip(left, -1.0, 1.0)
    if is_stereo:
        right_clamped = np.clip(right, -1.0, 1.0)

    sampwidth = 2 if bit_depth == 16 else 4

    with wave.open(filepath_or_buffer, "wb") as wf:
        wf.setnchannels(num_channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(sample_rate)

        if bit_depth == 16:
            # Scale to 16-bit signed int [-32767, 32767]
            i16_left = (left_clamped * 32767.0).astype(np.int16)
            if is_stereo:
                i16_right = (right_clamped * 32767.0).astype(np.int16)
                interleaved = np.empty((n_samples * 2,), dtype=np.int16)
                interleaved[0::2] = i16_left
                interleaved[1::2] = i16_right
                raw_bytes = interleaved.tobytes()
            else:
                raw_bytes = i16_left.tobytes()
            wf.writeframes(raw_bytes)
        else:
            # 32-bit float or 32-bit int
            i32_left = (left_clamped * 2147483647.0).astype(np.int32)
            if is_stereo:
                i32_right = (right_clamped * 2147483647.0).astype(np.int32)
                interleaved = np.empty((n_samples * 2,), dtype=np.int32)
                interleaved[0::2] = i32_left
                interleaved[1::2] = i32_right
                raw_bytes = interleaved.tobytes()
            else:
                raw_bytes = i32_left.tobytes()
            wf.writeframes(raw_bytes)


def read_wav(filepath_or_buffer: str | io.BytesIO) -> Tuple[np.ndarray, np.ndarray, int]:
    """Read standard WAV file into normalized float32 arrays [-1.0, 1.0]."""
    with wave.open(filepath_or_buffer, "rb") as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        sample_rate = wf.getframerate()
        n_frames = wf.getnframes()
        raw_bytes = wf.readframes(n_frames)

    if sampwidth == 2:
        data = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    elif sampwidth == 4:
        data = np.frombuffer(raw_bytes, dtype=np.int32).astype(np.float32) / 2147483648.0
    elif sampwidth == 1:
        data = (np.frombuffer(raw_bytes, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    else:
        raise ValueError(f"Unsupported sample width: {sampwidth}")

    if n_channels == 1:
        left = data
        right = data.copy()
    else:
        left = data[0::2]
        right = data[1::2]

    return left, right, sample_rate


def get_wav_bytes(
    left: np.ndarray,
    right: Optional[np.ndarray] = None,
    sample_rate: int = 44100,
    bit_depth: int = 16,
) -> bytes:
    """Convenience helper to encode audio directly to bytes in memory."""
    buf = io.BytesIO()
    write_wav(buf, left, right, sample_rate, bit_depth)
    return buf.getvalue()
