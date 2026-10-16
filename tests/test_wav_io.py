"""Tests for WAV file I/O and byte serialization."""

import io
import numpy as np
import pytest
from waveforge.audio.wav_io import write_wav, read_wav, get_wav_bytes


def test_wav_write_read_roundtrip():
    sr = 44100
    t = np.linspace(0, 0.1, int(sr * 0.1), endpoint=False)
    orig_left = (0.7 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    orig_right = (0.5 * np.cos(2 * np.pi * 880 * t)).astype(np.float32)

    buf = io.BytesIO()
    write_wav(buf, orig_left, orig_right, sample_rate=sr, bit_depth=16)

    buf.seek(0)
    read_l, read_r, read_sr = read_wav(buf)

    assert read_sr == sr
    assert len(read_l) == len(orig_left)
    assert len(read_r) == len(orig_right)
    # Check numerical accuracy (16-bit quantization error < 1e-4)
    assert np.allclose(read_l, orig_left, atol=1e-4)
    assert np.allclose(read_r, orig_right, atol=1e-4)


def test_get_wav_bytes():
    left = np.zeros(1024, dtype=np.float32)
    data = get_wav_bytes(left, sample_rate=44100)
    assert len(data) > 44  # Header is at least 44 bytes
    assert data[:4] == b"RIFF"
