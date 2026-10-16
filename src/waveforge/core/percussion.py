"""Authentic Roland TR-808 style analog drum synthesis algorithms: Kick, Snare, and 6-osc Hi-Hat."""

from __future__ import annotations
import math
import numpy as np
from waveforge.core.filters import BiquadFilter, FilterType


class Kick808:
    """Analog 808 Kick Drum with exponential pitch drop, attack click, and soft saturation."""

    def __init__(
        self,
        sample_rate: int = 44100,
        pitch_start: float = 220.0,
        pitch_end: float = 48.0,
        pitch_decay: float = 0.04,   # 40ms fast pitch dive
        decay_time: float = 0.6,     # 600ms body decay
        click_amount: float = 0.3,
        drive: float = 1.4,
    ):
        self.sample_rate = float(sample_rate)
        self.pitch_start = pitch_start
        self.pitch_end = pitch_end
        self.pitch_decay = max(0.005, pitch_decay)
        self.decay_time = max(0.05, decay_time)
        self.click_amount = click_amount
        self.drive = drive

        self._phase = 0.0
        self._current_sample = 0
        self._total_samples = 0
        self._active = False

    def trigger(self, velocity: float = 1.0) -> None:
        self._phase = 0.0
        self._current_sample = 0
        self._total_samples = int(self.decay_time * self.sample_rate * 1.5)
        self._velocity = velocity
        self._active = True

    def process_sample(self) -> float:
        if not self._active:
            return 0.0

        t_sec = self._current_sample / self.sample_rate
        if self._current_sample >= self._total_samples:
            self._active = False
            return 0.0

        # Exponential pitch envelope
        pitch_env = math.exp(-t_sec / self.pitch_decay)
        cur_freq = self.pitch_end + (self.pitch_start - self.pitch_end) * pitch_env

        # Phase increment
        dt = cur_freq / self.sample_rate
        self._phase = (self._phase + dt) % 1.0

        # Sine body
        sine_val = math.sin(2.0 * math.pi * self._phase)

        # Click transient in first 5ms
        click = 0.0
        if t_sec < 0.005:
            click = (1.0 - t_sec / 0.005) * self.click_amount

        # Amplitude envelope
        amp_env = math.exp(-t_sec / (self.decay_time * 0.35)) * self._velocity

        out = (sine_val + click) * amp_env
        # Soft saturation
        out = math.tanh(self.drive * out)

        self._current_sample += 1
        return float(out)


class Snare808:
    """Analog Snare combining dual tone oscillators and bandpass filtered snappy noise."""

    def __init__(
        self,
        sample_rate: int = 44100,
        tone_freq: float = 180.0,
        tone_decay: float = 0.15,
        snappy_decay: float = 0.25,
        snappy_mix: float = 0.65,
    ):
        self.sample_rate = float(sample_rate)
        self.tone_freq = tone_freq
        self.tone_decay = tone_decay
        self.snappy_decay = snappy_decay
        self.snappy_mix = snappy_mix

        self.bp_filter = BiquadFilter(
            sample_rate=sample_rate,
            filter_type=FilterType.BANDPASS,
            cutoff_hz=2400.0,
            q=2.0,
        )

        self._phase1 = 0.0
        self._phase2 = 0.0
        self._current_sample = 0
        self._total_samples = 0
        self._active = False
        self._velocity = 1.0
        self._rng = np.random.default_rng(seed=808)

    def trigger(self, velocity: float = 1.0) -> None:
        self._phase1 = 0.0
        self._phase2 = 0.0
        self._current_sample = 0
        self._total_samples = int(max(self.tone_decay, self.snappy_decay) * self.sample_rate * 2.0)
        self._velocity = velocity
        self._active = True
        self.bp_filter.reset_state()

    def process_sample(self) -> float:
        if not self._active:
            return 0.0

        t_sec = self._current_sample / self.sample_rate
        if self._current_sample >= self._total_samples:
            self._active = False
            return 0.0

        # Body: two sine tones (fundamental and harmonic ~1.8x)
        dt1 = self.tone_freq / self.sample_rate
        dt2 = (self.tone_freq * 1.8) / self.sample_rate
        self._phase1 = (self._phase1 + dt1) % 1.0
        self._phase2 = (self._phase2 + dt2) % 1.0

        body = (math.sin(2.0 * math.pi * self._phase1) + 0.6 * math.sin(2.0 * math.pi * self._phase2)) * 0.6
        body_env = math.exp(-t_sec / (self.tone_decay * 0.3))

        # Snappy noise burst through bandpass filter
        white = float(self._rng.uniform(-1.0, 1.0))
        noise_filtered = self.bp_filter.process_sample(white)
        noise_env = math.exp(-t_sec / (self.snappy_decay * 0.35))

        out = ((1.0 - self.snappy_mix) * (body * body_env) + self.snappy_mix * (noise_filtered * noise_env)) * self._velocity
        out = math.tanh(1.5 * out)

        self._current_sample += 1
        return float(out)


class HiHat808:
    """Authentic TR-808 6-oscillator inharmonic square cluster into resonant highpass."""

    # Exact Roland TR-808 square wave cluster frequencies
    CLUSTER_FREQS = [243.0, 340.0, 540.0, 800.0, 1080.0, 1200.0]

    def __init__(
        self,
        sample_rate: int = 44100,
        decay_time: float = 0.06,  # 60ms closed, ~350ms open
        cutoff_hz: float = 7200.0,
    ):
        self.sample_rate = float(sample_rate)
        self.decay_time = decay_time
        self.cutoff_hz = cutoff_hz

        self.hpf = BiquadFilter(
            sample_rate=sample_rate,
            filter_type=FilterType.HIGHPASS,
            cutoff_hz=cutoff_hz,
            q=2.5,
        )

        self._phases = [0.0] * 6
        self._current_sample = 0
        self._total_samples = 0
        self._active = False
        self._velocity = 1.0

    def trigger(self, velocity: float = 1.0, open_hat: bool = False) -> None:
        self._current_sample = 0
        decay = 0.35 if open_hat else self.decay_time
        self._total_samples = int(decay * self.sample_rate * 2.0)
        self._active_decay = decay
        self._velocity = velocity
        self._active = True
        self.hpf.reset_state()

    def process_sample(self) -> float:
        if not self._active:
            return 0.0

        t_sec = self._current_sample / self.sample_rate
        if self._current_sample >= self._total_samples:
            self._active = False
            return 0.0

        # Sum 6 square oscillators
        sum_sq = 0.0
        for i, freq in enumerate(self.CLUSTER_FREQS):
            dt = freq / self.sample_rate
            self._phases[i] = (self._phases[i] + dt) % 1.0
            sum_sq += 1.0 if self._phases[i] < 0.5 else -1.0

        # Highpass filter to isolate the metallic sizzle
        metallic = self.hpf.process_sample(sum_sq * (1.0 / 6.0))

        # Sharp exponential decay
        amp_env = math.exp(-t_sec / (self._active_decay * 0.3)) * self._velocity
        out = math.tanh(metallic * amp_env * 1.8)

        self._current_sample += 1
        return float(out)
