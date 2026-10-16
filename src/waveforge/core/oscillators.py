"""Anti-aliased PolyBLEP (Polynomial Band-Limited Step) audio oscillators."""

from __future__ import annotations
import math
import numpy as np
from waveforge.core.config import WaveformType


def polyblep_residual(t: float, dt: float) -> float:
    """Compute 2nd-order PolyBLEP residual for step discontinuity at t=0.

    Args:
        t: Normalized phase in [0, 1)
        dt: Normalized frequency increment (f0 / fs)
    """
    if dt <= 0.0:
        return 0.0

    # Near beginning of cycle [0, dt)
    if t < dt:
        x = t / dt
        return 2.0 * x - x * x - 1.0

    # Near end of cycle (1 - dt, 1)
    if t > (1.0 - dt):
        x = (t - 1.0) / dt
        return x * x + 2.0 * x + 1.0

    return 0.0


def polyblamp_residual(t: float, dt: float) -> float:
    """Compute 3rd-order PolyBLAMP residual for slope discontinuity at t=0."""
    if dt <= 0.0:
        return 0.0

    if t < dt:
        x = t / dt
        return (dt / 3.0) * (x * x * x - 3.0 * x * x + 2.0)
    elif t > (1.0 - dt):
        x = (1.0 - t) / dt
        return (dt / 3.0) * (x * x * x - 3.0 * x * x + 2.0)
    return 0.0


class PinkNoiseFilter:
    """Paul Kellet's 3-pole IIR filter for authentic -3dB/octave pink noise."""

    def __init__(self):
        self.b0 = 0.0
        self.b1 = 0.0
        self.b2 = 0.0

    def process_sample(self, white: float) -> float:
        self.b0 = 0.99765 * self.b0 + white * 0.0990460
        self.b1 = 0.96300 * self.b1 + white * 0.2965164
        self.b2 = 0.57000 * self.b2 + white * 1.0526913
        pink = self.b0 + self.b1 + self.b2 + white * 0.1848
        return pink * 0.18  # Normalize to approximately [-1.0, 1.0]


class PolyBLEPOscillator:
    """Anti-aliased oscillator featuring PolyBLEP algorithm for alias-free synthesis."""

    def __init__(
        self,
        sample_rate: int = 44100,
        frequency: float = 440.0,
        waveform: WaveformType = WaveformType.SAW,
        pulse_width: float = 0.5,
        phase: float = 0.0,
    ):
        self.sample_rate = float(sample_rate)
        self.frequency = float(frequency)
        self.waveform = waveform
        self.pulse_width = float(pulse_width)
        self.phase = float(phase) % 1.0
        self.pink_filter = PinkNoiseFilter()

        # For integrated triangle wave
        self._tri_integrator = -1.0
        self._dc_prev_in = 0.0
        self._dc_prev_out = 0.0
        self._rng = np.random.default_rng(seed=42)

    def set_sample_rate(self, sr: int) -> None:
        self.sample_rate = float(sr)

    def set_frequency(self, freq: float) -> None:
        # Clamp frequency below Nyquist to prevent instability
        nyquist = self.sample_rate * 0.499
        self.frequency = max(0.1, min(float(freq), nyquist))

    def set_waveform(self, waveform: WaveformType) -> None:
        self.waveform = waveform

    def set_pulse_width(self, pw: float) -> None:
        # Clamp pulse width between 0.01 and 0.99
        self.pulse_width = max(0.01, min(0.99, float(pw)))

    def reset_phase(self, phase: float = 0.0) -> None:
        self.phase = float(phase) % 1.0
        self._tri_integrator = -1.0
        self._dc_prev_in = 0.0
        self._dc_prev_out = 0.0

    def process_sample(
        self,
        freq_mod: float = 0.0,
        phase_mod: float = 0.0,
        sync_trigger: bool = False,
    ) -> float:
        """Calculate single audio sample with optional frequency/phase modulation."""
        if sync_trigger:
            self.phase = 0.0

        effective_freq = max(0.1, min(self.frequency + freq_mod, self.sample_rate * 0.499))
        dt = effective_freq / self.sample_rate

        # Effective phase including phase modulation
        curr_phase = (self.phase + phase_mod) % 1.0

        sample = 0.0

        if self.waveform == WaveformType.SINE:
            sample = math.sin(2.0 * math.pi * curr_phase)

        elif self.waveform == WaveformType.SAW:
            # Naive sawtooth: ramp from -1.0 to 1.0
            naive_saw = 2.0 * curr_phase - 1.0
            # PolyBLEP residual removes the high-frequency step discontinuity
            sample = naive_saw - polyblep_residual(curr_phase, dt)

        elif self.waveform == WaveformType.SQUARE:
            # Pulse wave with arbitrary duty cycle (pulse width)
            pw = self.pulse_width
            naive_square = 1.0 if curr_phase < pw else -1.0
            # Correct step discontinuity at phase 0
            sample = naive_square + polyblep_residual(curr_phase, dt)
            # Correct step discontinuity at phase pw
            shifted_phase = (curr_phase - pw + 1.0) % 1.0
            sample -= polyblep_residual(shifted_phase, dt)

        elif self.waveform == WaveformType.TRIANGLE:
            # Analytical integration of PolyBLEP square wave generates pure anti-aliased triangle
            pw = 0.5
            naive_sq = 1.0 if curr_phase < pw else -1.0
            sq_blep = naive_sq + polyblep_residual(curr_phase, dt) - polyblep_residual((curr_phase - pw + 1.0) % 1.0, dt)
            self._tri_integrator += 4.0 * dt * sq_blep
            # High-pass DC-blocker
            raw = self._tri_integrator
            hp = raw - self._dc_prev_in + 0.999 * self._dc_prev_out
            self._dc_prev_in = raw
            self._dc_prev_out = hp
            sample = max(-1.0, min(1.0, hp))

        elif self.waveform == WaveformType.NOISE:
            white = float(self._rng.uniform(-1.0, 1.0))
            sample = self.pink_filter.process_sample(white)

        # Advance phase accumulator
        self.phase = (self.phase + dt) % 1.0
        return sample

    def process_block(
        self,
        num_samples: int,
        freq_mod: Optional[np.ndarray] = None,
        phase_mod: Optional[np.ndarray] = None,
        sync_triggers: Optional[np.ndarray] = None,
        output: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """Process a block of samples with optional audio-rate modulation vectors."""
        if output is None:
            output = np.zeros(num_samples, dtype=np.float32)

        has_fm = freq_mod is not None
        has_pm = phase_mod is not None
        has_sync = sync_triggers is not None

        for i in range(num_samples):
            fm = float(freq_mod[i]) if has_fm else 0.0
            pm = float(phase_mod[i]) if has_pm else 0.0
            sync = bool(sync_triggers[i] > 0.5) if has_sync else False
            output[i] = self.process_sample(fm, pm, sync)

        return output
