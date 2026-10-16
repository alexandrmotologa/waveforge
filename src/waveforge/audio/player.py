"""Audio playback driver supporting sounddevice and native Windows winsound memory streaming."""

from __future__ import annotations
import sys
import time
import numpy as np
from typing import Optional
from waveforge.audio.wav_io import get_wav_bytes


class AudioPlayer:
    """Plays audio buffers in real-time."""

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self._has_sounddevice = False
        try:
            import sounddevice as sd  # noqa
            self._has_sounddevice = True
        except ImportError:
            self._has_sounddevice = False

    def play_buffer(
        self,
        left: np.ndarray,
        right: Optional[np.ndarray] = None,
        sample_rate: Optional[int] = None,
        blocking: bool = True,
    ) -> bool:
        """Play stereo/mono audio buffer."""
        sr = sample_rate or self.sample_rate

        if self._has_sounddevice:
            import sounddevice as sd
            if right is not None:
                stereo_data = np.stack([left, right], axis=1).astype(np.float32)
            else:
                stereo_data = left.astype(np.float32)
            sd.play(stereo_data, samplerate=sr)
            if blocking:
                sd.wait()
            return True

        # Fallback for Windows native winsound
        if sys.platform == "win32":
            import winsound
            wav_bytes = get_wav_bytes(left, right, sample_rate=sr, bit_depth=16)
            flags = winsound.SND_MEMORY
            if not blocking:
                flags |= winsound.SND_ASYNC
            winsound.PlaySound(wav_bytes, flags)
            return True

        return False

    def play_wav_file(self, filepath: str, blocking: bool = True) -> bool:
        """Play WAV audio from file."""
        if self._has_sounddevice:
            from waveforge.audio.wav_io import read_wav
            l, r, sr = read_wav(filepath)
            return self.play_buffer(l, r, sample_rate=sr, blocking=blocking)

        if sys.platform == "win32":
            import winsound
            flags = winsound.SND_FILENAME
            if not blocking:
                flags |= winsound.SND_ASYNC
            winsound.PlaySound(filepath, flags)
            return True

        return False
