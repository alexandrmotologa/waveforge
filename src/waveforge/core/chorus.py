"""Stereo Bucket Brigade Device (BBD) Chorus and Flanger with quadrature LFOs."""

from __future__ import annotations
import math
import numpy as np
from typing import Tuple, Optional
from waveforge.core.buffer import CircularBuffer


class StereoChorusEffect:
    """Stereo BBD-style Chorus / Flanger with dual quadrature LFOs (90 deg phase split)."""

    def __init__(
        self,
        sample_rate: int = 44100,
        rate_hz: float = 1.2,
        depth_ms: float = 3.5,
        base_delay_ms: float = 15.0,
        feedback: float = 0.25,
        mix: float = 0.5,
        flanger_mode: bool = False,
    ):
        self.sample_rate = float(sample_rate)
        self.rate_hz = max(0.05, min(10.0, float(rate_hz)))
        self.depth_ms = max(0.1, min(15.0, float(depth_ms)))
        self.base_delay_ms = max(1.0, min(40.0, float(base_delay_ms)))
        self.feedback = max(-0.95, min(0.95, float(feedback)))
        self.mix = max(0.0, min(1.0, float(mix)))
        self.flanger_mode = flanger_mode

        if flanger_mode:
            self.base_delay_ms = 2.5
            self.depth_ms = 1.8

        # 100ms maximum delay buffer is plenty for chorus/flange
        max_samples = int(self.sample_rate * 0.1)
        self.buffer = CircularBuffer(max_samples=max_samples, channels=2)

        self._lfo_phase = 0.0
        self._fb_l = 0.0
        self._fb_r = 0.0

    def set_sample_rate(self, sr: int) -> None:
        self.sample_rate = float(sr)
        max_samples = int(self.sample_rate * 0.1)
        self.buffer = CircularBuffer(max_samples=max_samples, channels=2)
        self._fb_l = 0.0
        self._fb_r = 0.0

    def reset_state(self) -> None:
        self._lfo_phase = 0.0
        self._fb_l = 0.0
        self._fb_r = 0.0

    def process_sample(self, in_l: float, in_r: float) -> Tuple[float, float]:
        # Dual quadrature LFO (90 deg / pi/2 phase difference between channels)
        lfo_l = math.sin(2.0 * math.pi * self._lfo_phase)
        lfo_r = math.cos(2.0 * math.pi * self._lfo_phase)

        # Modulated delay times in samples
        d_l_sec = (self.base_delay_ms + self.depth_ms * lfo_l) * 0.001
        d_r_sec = (self.base_delay_ms + self.depth_ms * lfo_r) * 0.001

        delay_samples_l = max(1.0, d_l_sec * self.sample_rate)
        delay_samples_r = max(1.0, d_r_sec * self.sample_rate)

        # Fractional read with Hermite 3rd-order interpolation
        wet_l = self.buffer.read_sample_hermite(delay_samples_l, channel=0)
        wet_r = self.buffer.read_sample_hermite(delay_samples_r, channel=1)

        # Write input + feedback into buffer
        write_l = in_l + wet_l * self.feedback
        write_r = in_r + wet_r * self.feedback

        if abs(write_l) > 1.0:
            write_l = math.tanh(write_l)
        if abs(write_r) > 1.0:
            write_r = math.tanh(write_r)

        self.buffer.write_sample([write_l, write_r])

        # Advance LFO phase
        self._lfo_phase = (self._lfo_phase + self.rate_hz / self.sample_rate) % 1.0

        # Dry / Wet sum
        dry = 1.0 - self.mix
        wet = self.mix
        out_l = dry * in_l + wet * wet_l
        out_r = dry * in_r + wet * wet_r

        return out_l, out_r
