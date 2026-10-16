"""Audio buffer abstractions, zero-allocation block buffers, and circular delay lines."""

from __future__ import annotations
import math
import numpy as np
from typing import Tuple, Optional


class AudioBuffer:
    """Multi-channel contiguous float32/float64 audio buffer."""

    def __init__(self, channels: int = 1, length: int = 128, dtype=np.float32):
        self.channels = channels
        self.length = length
        self.dtype = dtype
        self.data = np.zeros((channels, length), dtype=dtype)

    def clear(self) -> None:
        """Zero out all channels in place."""
        self.data.fill(0.0)

    def fill(self, value: float) -> None:
        """Fill buffer with constant value."""
        self.data.fill(value)

    def copy_from(self, source: AudioBuffer | np.ndarray) -> None:
        """Copy data from another buffer or numpy array."""
        if isinstance(source, AudioBuffer):
            np.copyto(self.data, source.data)
        else:
            np.copyto(self.data, source)

    def add(self, source: AudioBuffer | np.ndarray, gain: float = 1.0) -> None:
        """In-place accumulate with optional gain."""
        if isinstance(source, AudioBuffer):
            self.data += source.data * gain
        else:
            self.data += source * gain

    def scale(self, gain: float) -> None:
        """Scale buffer in place."""
        self.data *= gain

    def get_channel(self, ch: int = 0) -> np.ndarray:
        """Get view of single channel array."""
        return self.data[ch]

    def peak(self) -> float:
        """Calculate maximum absolute amplitude across all channels."""
        return float(np.max(np.abs(self.data)))

    def rms(self) -> float:
        """Calculate Root Mean Square energy across all channels."""
        return float(np.sqrt(np.mean(self.data ** 2)))

    def clamp(self, min_val: float = -1.0, max_val: float = 1.0) -> None:
        """Hard clamp values in place."""
        np.clip(self.data, min_val, max_val, out=self.data)

    def soft_clip(self) -> None:
        """Apply soft saturation using tanh in place."""
        np.tanh(self.data, out=self.data)


class CircularBuffer:
    """Ring buffer supporting fractional sample reads with Hermite interpolation."""

    def __init__(self, max_samples: int, channels: int = 1, dtype=np.float32):
        # Round up to power of 2 for fast bitwise masking
        self.size = 1 << (max_samples - 1).bit_length()
        self.mask = self.size - 1
        self.channels = channels
        self.buffer = np.zeros((channels, self.size), dtype=dtype)
        self.write_idx = 0

    def write_sample(self, values: np.ndarray | list[float] | float) -> None:
        """Write single frame across channels and advance write pointer."""
        if np.isscalar(values):
            self.buffer[0, self.write_idx] = float(values)
        else:
            for ch in range(self.channels):
                self.buffer[ch, self.write_idx] = values[ch]
        self.write_idx = (self.write_idx + 1) & self.mask

    def write_block(self, block: np.ndarray) -> None:
        """Write block of samples [channels, block_size] into ring buffer."""
        length = block.shape[-1]
        for i in range(length):
            idx = (self.write_idx + i) & self.mask
            self.buffer[:, idx] = block[:, i]
        self.write_idx = (self.write_idx + length) & self.mask

    def read_sample_linear(self, delay_samples: float, channel: int = 0) -> float:
        """Read sample with linear fractional interpolation."""
        read_pos = float(self.write_idx) - delay_samples
        idx0 = int(math.floor(read_pos))
        frac = read_pos - idx0

        i0 = idx0 & self.mask
        i1 = (idx0 + 1) & self.mask

        y0 = self.buffer[channel, i0]
        y1 = self.buffer[channel, i1]
        return float(y0 + frac * (y1 - y0))

    def read_sample_hermite(self, delay_samples: float, channel: int = 0) -> float:
        """4-point 3rd-order Hermite polynomial interpolation for high-frequency preservation."""
        read_pos = float(self.write_idx) - delay_samples
        idx = int(math.floor(read_pos))
        frac = read_pos - idx

        im1 = (idx - 1) & self.mask
        i0 = idx & self.mask
        i1 = (idx + 1) & self.mask
        i2 = (idx + 2) & self.mask

        y_m1 = self.buffer[channel, im1]
        y0 = self.buffer[channel, i0]
        y1 = self.buffer[channel, i1]
        y2 = self.buffer[channel, i2]

        # 4-point, 3rd-order Hermite interpolation
        c0 = y0
        c1 = 0.5 * (y1 - y_m1)
        c2 = y_m1 - 2.5 * y0 + 2.0 * y1 - 0.5 * y2
        c3 = 0.5 * (y2 - y_m1) + 1.5 * (y0 - y1)

        return float(((c3 * frac + c2) * frac + c1) * frac + c0)
