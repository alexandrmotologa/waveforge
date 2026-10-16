"""Modulation sources: Low Frequency Oscillators (LFO), Sample & Hold, and Envelope Followers."""

from __future__ import annotations
import math
import numpy as np
from typing import Optional
from waveforge.core.config import LFOType


class LFO:
    """Low-Frequency Oscillator for cyclic parameter modulation."""

    def __init__(
        self,
        sample_rate: int = 44100,
        rate_hz: float = 2.0,
        lfo_type: LFOType = LFOType.SINE,
        depth: float = 1.0,
        bipolar: bool = True,
    ):
        self.sample_rate = float(sample_rate)
        self.rate_hz = float(rate_hz)
        self.lfo_type = lfo_type
        self.depth = float(depth)
        self.bipolar = bipolar

        self.phase = 0.0
        self._sh_value = 0.0
        self._rng = np.random.default_rng(seed=123)

    def set_sample_rate(self, sr: int) -> None:
        self.sample_rate = float(sr)

    def set_rate(self, rate_hz: float) -> None:
        self.rate_hz = max(0.01, min(float(rate_hz), 100.0))

    def reset_phase(self, phase: float = 0.0) -> None:
        self.phase = float(phase) % 1.0

    def process_sample(self, sync_trigger: bool = False) -> float:
        """Generate next LFO value."""
        if sync_trigger:
            self.phase = 0.0

        dt = self.rate_hz / self.sample_rate
        p = self.phase
        val = 0.0

        if self.lfo_type == LFOType.SINE:
            val = math.sin(2.0 * math.pi * p)

        elif self.lfo_type == LFOType.TRIANGLE:
            # -1.0 to 1.0 triangle
            val = 4.0 * abs(p - 0.5) - 1.0

        elif self.lfo_type == LFOType.SAW_UP:
            val = 2.0 * p - 1.0

        elif self.lfo_type == LFOType.SAW_DOWN:
            val = 1.0 - 2.0 * p

        elif self.lfo_type == LFOType.SQUARE:
            val = 1.0 if p < 0.5 else -1.0

        elif self.lfo_type == LFOType.SAMPLE_HOLD:
            if self.phase + dt >= 1.0 or self.phase == 0.0:
                self._sh_value = float(self._rng.uniform(-1.0, 1.0))
            val = self._sh_value

        # Advance phase
        self.phase = (self.phase + dt) % 1.0

        # Adjust unipolar vs bipolar
        if not self.bipolar:
            val = 0.5 * (val + 1.0)  # Map [-1, 1] to [0, 1]

        return float(val * self.depth)

    def process_block(
        self,
        num_samples: int,
        sync_triggers: Optional[np.ndarray] = None,
        output: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        if output is None:
            output = np.zeros(num_samples, dtype=np.float32)

        has_sync = sync_triggers is not None
        for i in range(num_samples):
            st = bool(sync_triggers[i] > 0.5) if has_sync else False
            output[i] = self.process_sample(st)

        return output


class SampleAndHold:
    """Sample & Hold module latching an input signal on clock rising edges."""

    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold
        self.held_value = 0.0
        self._prev_clock = 0.0
        self._rng = np.random.default_rng(seed=321)

    def process_sample(self, input_sig: Optional[float], clock_sig: float) -> float:
        # Detect rising edge on clock signal
        if clock_sig >= self.threshold and self._prev_clock < self.threshold:
            if input_sig is not None:
                self.held_value = float(input_sig)
            else:
                self.held_value = float(self._rng.uniform(-1.0, 1.0))

        self._prev_clock = clock_sig
        return self.held_value


class EnvelopeFollower:
    """Dynamic peak envelope follower with independent attack and release ballistics."""

    def __init__(
        self,
        sample_rate: int = 44100,
        attack_time: float = 0.01,   # 10ms
        release_time: float = 0.1,  # 100ms
    ):
        self.sample_rate = float(sample_rate)
        self.attack_time = max(0.0001, float(attack_time))
        self.release_time = max(0.0001, float(release_time))
        self.envelope = 0.0
        self._recompute_coefficients()

    def set_sample_rate(self, sr: int) -> None:
        self.sample_rate = float(sr)
        self._recompute_coefficients()

    def _recompute_coefficients(self) -> None:
        self._ga = math.exp(-1.0 / (self.attack_time * self.sample_rate))
        self._gr = math.exp(-1.0 / (self.release_time * self.sample_rate))

    def process_sample(self, x: float) -> float:
        abs_x = abs(x)
        if abs_x > self.envelope:
            self.envelope = self._ga * self.envelope + (1.0 - self._ga) * abs_x
        else:
            self.envelope = self._gr * self.envelope + (1.0 - self._gr) * abs_x
        return float(self.envelope)
