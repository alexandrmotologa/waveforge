"""Karplus-Strong physical modeling plucked string synthesis algorithm."""

from __future__ import annotations
import math
import numpy as np
from typing import Optional
from waveforge.core.buffer import CircularBuffer
from waveforge.core.filters import BiquadFilter, FilterType


class KarplusStrongString:
    """Karplus-Strong string synthesis: noise burst excitation into filtered delay loop."""

    def __init__(
        self,
        sample_rate: int = 44100,
        frequency: float = 220.0,
        decay: float = 0.985,
        damping: float = 0.35,
    ):
        self.sample_rate = float(sample_rate)
        self.frequency = max(20.0, min(float(frequency), 4000.0))
        self.decay = max(0.5, min(float(decay), 0.999))
        self.damping = max(0.0, min(float(damping), 0.95))

        # Circular buffer for delay loop (max 0.1s is enough down to 20Hz: 44100/20 = 2205 samples)
        self.buffer = CircularBuffer(max_samples=4096, channels=1)

        # Internal one-pole filter state in feedback loop: y[n] = (1-d)*x[n] + d*y[n-1]
        self._filter_state = 0.0

        # Burst state: how many samples of excitation noise left
        self._burst_samples_left = 0
        self._rng = np.random.default_rng(seed=777)

    def set_sample_rate(self, sr: int) -> None:
        self.sample_rate = float(sr)
        self.buffer = CircularBuffer(max_samples=4096, channels=1)
        self._filter_state = 0.0

    def set_frequency(self, freq: float) -> None:
        self.frequency = max(20.0, min(float(freq), self.sample_rate * 0.45))

    def trigger_pluck(self, velocity: float = 1.0) -> None:
        """Inject short burst of white noise into the delay line to simulate a pluck."""
        delay_len = max(2, int(round(self.sample_rate / self.frequency)))
        # Fill buffer with excitation noise
        self._burst_samples_left = delay_len
        self._filter_state = 0.0

    def process_sample(self, external_excitation: Optional[float] = None) -> float:
        """Process one sample through the physical modeling feedback loop."""
        delay_samples = self.sample_rate / self.frequency

        # Read sample from circular buffer with Hermite interpolation
        delayed = self.buffer.read_sample_hermite(delay_samples, channel=0)

        # Lowpass filter in loop simulating string mechanical damping:
        # y = (1 - damping) * delayed + damping * y_prev
        filtered = (1.0 - self.damping) * delayed + self.damping * self._filter_state
        self._filter_state = filtered

        # Apply loop decay (energy loss per reflection)
        feedback_val = filtered * self.decay

        # Add excitation (either noise burst from trigger or external input)
        excitation = 0.0
        if external_excitation is not None and abs(external_excitation) > 1e-5:
            excitation = external_excitation
        elif self._burst_samples_left > 0:
            excitation = float(self._rng.uniform(-0.9, 0.9))
            self._burst_samples_left -= 1

        injected = excitation + feedback_val
        # Soft clamp in loop to keep strictly stable
        if abs(injected) > 1.0:
            injected = math.tanh(injected)

        self.buffer.write_sample(injected)
        return float(injected)

    def process_block(
        self,
        num_samples: int,
        freq_mod: Optional[np.ndarray] = None,
        trigger_triggers: Optional[np.ndarray] = None,
        output: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        if output is None:
            output = np.zeros(num_samples, dtype=np.float32)

        has_fm = freq_mod is not None
        has_trig = trigger_triggers is not None

        base_freq = self.frequency
        for i in range(num_samples):
            if has_trig and trigger_triggers[i] > 0.5:
                self.trigger_pluck()

            if has_fm:
                self.set_frequency(base_freq + float(freq_mod[i]))

            output[i] = self.process_sample()

        return output
