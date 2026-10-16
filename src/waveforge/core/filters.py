"""Authentic Digital Signal Processing Biquad filters and Chamberlin State Variable Filter (SVF).

Implements exact Robert Bristow-Johnson Audio EQ Cookbook difference equations in
Direct Form II Transposed (DF2T) topology and Hal Chamberlin 2-pole SVF.
"""

from __future__ import annotations
import math
import numpy as np
from typing import Tuple, Optional
from waveforge.core.config import FilterType, FilterTopology


class BiquadCoefficients:
    """Normalized filter coefficients (a0 normalized to 1.0)."""

    def __init__(
        self,
        b0: float = 1.0,
        b1: float = 0.0,
        b2: float = 0.0,
        a1: float = 0.0,
        a2: float = 0.0,
    ):
        self.b0 = b0
        self.b1 = b1
        self.b2 = b2
        self.a1 = a1
        self.a2 = a2


def compute_rbj_coefficients(
    filter_type: FilterType,
    cutoff_hz: float,
    sample_rate: float,
    q: float = 0.7071,
    gain_db: float = 0.0,
) -> BiquadCoefficients:
    """Compute exact Robert Bristow-Johnson Audio EQ Cookbook coefficients.

    Args:
        filter_type: Lowpass, Highpass, Bandpass, Notch, Peak, Shelves, or Allpass.
        cutoff_hz: Filter corner / center frequency in Hz.
        sample_rate: Sampling frequency in Hz.
        q: Filter quality / resonance factor (Butterworth = 0.7071).
        gain_db: Filter boost or cut gain in decibels.
    """
    # Clamp cutoff to safe bounds below Nyquist to avoid numerical singularity
    nyquist = sample_rate * 0.495
    f0 = max(10.0, min(cutoff_hz, nyquist))
    q_val = max(0.01, min(q, 50.0))

    omega = 2.0 * math.pi * f0 / sample_rate
    cos_w = math.cos(omega)
    sin_w = math.sin(omega)
    alpha = sin_w / (2.0 * q_val)

    # Gain amplitude for peaking and shelf filters
    A = 10.0 ** (gain_db / 40.0)

    b0 = b1 = b2 = a0 = a1 = a2 = 0.0

    if filter_type == FilterType.LOWPASS:
        b0 = (1.0 - cos_w) * 0.5
        b1 = 1.0 - cos_w
        b2 = (1.0 - cos_w) * 0.5
        a0 = 1.0 + alpha
        a1 = -2.0 * cos_w
        a2 = 1.0 - alpha

    elif filter_type == FilterType.HIGHPASS:
        b0 = (1.0 + cos_w) * 0.5
        b1 = -(1.0 + cos_w)
        b2 = (1.0 + cos_w) * 0.5
        a0 = 1.0 + alpha
        a1 = -2.0 * cos_w
        a2 = 1.0 - alpha

    elif filter_type == FilterType.BANDPASS:
        # Constant 0 dB peak gain bandpass
        b0 = alpha
        b1 = 0.0
        b2 = -alpha
        a0 = 1.0 + alpha
        a1 = -2.0 * cos_w
        a2 = 1.0 - alpha

    elif filter_type == FilterType.NOTCH:
        b0 = 1.0
        b1 = -2.0 * cos_w
        b2 = 1.0
        a0 = 1.0 + alpha
        a1 = -2.0 * cos_w
        a2 = 1.0 - alpha

    elif filter_type == FilterType.ALLPASS:
        b0 = 1.0 - alpha
        b1 = -2.0 * cos_w
        b2 = 1.0 + alpha
        a0 = 1.0 + alpha
        a1 = -2.0 * cos_w
        a2 = 1.0 - alpha

    elif filter_type == FilterType.PEAK:
        b0 = 1.0 + alpha * A
        b1 = -2.0 * cos_w
        b2 = 1.0 - alpha * A
        a0 = 1.0 + alpha / A
        a1 = -2.0 * cos_w
        a2 = 1.0 - alpha / A

    elif filter_type == FilterType.LOW_SHELF:
        sqrt_A = math.sqrt(A)
        two_sqrt_a_alpha = 2.0 * sqrt_A * alpha
        b0 = A * ((A + 1.0) - (A - 1.0) * cos_w + two_sqrt_a_alpha)
        b1 = 2.0 * A * ((A - 1.0) - (A + 1.0) * cos_w)
        b2 = A * ((A + 1.0) - (A - 1.0) * cos_w - two_sqrt_a_alpha)
        a0 = (A + 1.0) + (A - 1.0) * cos_w + two_sqrt_a_alpha
        a1 = -2.0 * ((A - 1.0) + (A + 1.0) * cos_w)
        a2 = (A + 1.0) + (A - 1.0) * cos_w - two_sqrt_a_alpha

    elif filter_type == FilterType.HIGH_SHELF:
        sqrt_A = math.sqrt(A)
        two_sqrt_a_alpha = 2.0 * sqrt_A * alpha
        b0 = A * ((A + 1.0) + (A - 1.0) * cos_w + two_sqrt_a_alpha)
        b1 = -2.0 * A * ((A - 1.0) + (A + 1.0) * cos_w)
        b2 = A * ((A + 1.0) + (A - 1.0) * cos_w - two_sqrt_a_alpha)
        a0 = (A + 1.0) - (A - 1.0) * cos_w + two_sqrt_a_alpha
        a1 = 2.0 * ((A - 1.0) - (A + 1.0) * cos_w)
        a2 = (A + 1.0) - (A - 1.0) * cos_w - two_sqrt_a_alpha

    # Normalize by a0
    inv_a0 = 1.0 / a0
    return BiquadCoefficients(
        b0=b0 * inv_a0,
        b1=b1 * inv_a0,
        b2=b2 * inv_a0,
        a1=a1 * inv_a0,
        a2=a2 * inv_a0,
    )


class BiquadFilter:
    """Biquad IIR filter using Direct Form II Transposed (DF2T) architecture."""

    def __init__(
        self,
        sample_rate: int = 44100,
        filter_type: FilterType = FilterType.LOWPASS,
        cutoff_hz: float = 1000.0,
        q: float = 0.7071,
        gain_db: float = 0.0,
    ):
        self.sample_rate = float(sample_rate)
        self.filter_type = filter_type
        self.cutoff_hz = float(cutoff_hz)
        self.q = float(q)
        self.gain_db = float(gain_db)

        # State delay registers for DF2T (z1, z2)
        self.z1 = 0.0
        self.z2 = 0.0

        # Coefficients
        self.coeffs = BiquadCoefficients()
        self._recompute_coefficients()

    def _recompute_coefficients(self) -> None:
        self.coeffs = compute_rbj_coefficients(
            self.filter_type,
            self.cutoff_hz,
            self.sample_rate,
            self.q,
            self.gain_db,
        )

    def set_sample_rate(self, sr: int) -> None:
        self.sample_rate = float(sr)
        self._recompute_coefficients()

    def set_params(
        self,
        filter_type: Optional[FilterType] = None,
        cutoff_hz: Optional[float] = None,
        q: Optional[float] = None,
        gain_db: Optional[float] = None,
    ) -> None:
        changed = False
        if filter_type is not None and filter_type != self.filter_type:
            self.filter_type = filter_type
            changed = True
        if cutoff_hz is not None and abs(cutoff_hz - self.cutoff_hz) > 1e-4:
            self.cutoff_hz = float(cutoff_hz)
            changed = True
        if q is not None and abs(q - self.q) > 1e-4:
            self.q = float(q)
            changed = True
        if gain_db is not None and abs(gain_db - self.gain_db) > 1e-4:
            self.gain_db = float(gain_db)
            changed = True

        if changed:
            self._recompute_coefficients()

    def reset_state(self) -> None:
        self.z1 = 0.0
        self.z2 = 0.0

    def process_sample(self, x: float) -> float:
        """Process single sample using Direct Form II Transposed difference equation."""
        c = self.coeffs
        # DF2T difference equations:
        # y[n] = b0 * x[n] + z1[n-1]
        # z1[n] = b1 * x[n] - a1 * y[n] + z2[n-1]
        # z2[n] = b2 * x[n] - a2 * y[n]
        y = c.b0 * x + self.z1
        self.z1 = c.b1 * x - c.a1 * y + self.z2
        self.z2 = c.b2 * x - c.a2 * y

        # Flush denormals to prevent floating-point CPU stall
        if abs(self.z1) < 1e-15:
            self.z1 = 0.0
        if abs(self.z2) < 1e-15:
            self.z2 = 0.0

        return y

    def process_block(
        self,
        input_block: np.ndarray,
        cutoff_mod: Optional[np.ndarray] = None,
        output_block: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """Process a block of audio samples with optional audio-rate cutoff modulation."""
        n = len(input_block)
        if output_block is None:
            output_block = np.zeros(n, dtype=np.float32)

        if cutoff_mod is None:
            # Constant coefficients - fast path
            c = self.coeffs
            b0, b1, b2, a1, a2 = c.b0, c.b1, c.b2, c.a1, c.a2
            z1, z2 = self.z1, self.z2

            for i in range(n):
                x = float(input_block[i])
                y = b0 * x + z1
                z1 = b1 * x - a1 * y + z2
                z2 = b2 * x - a2 * y
                output_block[i] = y

            self.z1 = 0.0 if abs(z1) < 1e-15 else z1
            self.z2 = 0.0 if abs(z2) < 1e-15 else z2
        else:
            # Per-sample dynamic modulation
            base_cutoff = self.cutoff_hz
            for i in range(n):
                dyn_cutoff = max(10.0, base_cutoff + float(cutoff_mod[i]))
                # Recompute coefficients dynamically
                c = compute_rbj_coefficients(
                    self.filter_type, dyn_cutoff, self.sample_rate, self.q, self.gain_db
                )
                x = float(input_block[i])
                y = c.b0 * x + self.z1
                self.z1 = c.b1 * x - c.a1 * y + self.z2
                self.z2 = c.b2 * x - c.a2 * y
                output_block[i] = y

        return output_block


class StateVariableFilter:
    """Chamberlin 2-Pole State Variable Filter (SVF) with 2x oversampling.

    Simultaneously produces Lowpass, Highpass, Bandpass, and Notch responses.
    """

    def __init__(
        self,
        sample_rate: int = 44100,
        cutoff_hz: float = 1000.0,
        resonance: float = 0.7071,
    ):
        self.sample_rate = float(sample_rate)
        self.cutoff_hz = float(cutoff_hz)
        self.resonance = float(resonance)

        self.lp = 0.0
        self.bp = 0.0
        self.hp = 0.0
        self.notch = 0.0

    def set_sample_rate(self, sr: int) -> None:
        self.sample_rate = float(sr)

    def set_params(self, cutoff_hz: float, resonance: float) -> None:
        self.cutoff_hz = max(10.0, min(float(cutoff_hz), self.sample_rate * 0.49))
        self.resonance = max(0.01, min(float(resonance), 20.0))

    def reset_state(self) -> None:
        self.lp = 0.0
        self.bp = 0.0
        self.hp = 0.0
        self.notch = 0.0

    def process_sample(self, x: float) -> Tuple[float, float, float, float]:
        """Process one sample with 2x oversampling.

        Returns:
            Tuple of (lowpass, highpass, bandpass, notch)
        """
        # Internal 2x oversampling sample rate
        f = 2.0 * math.sin(math.pi * self.cutoff_hz / (self.sample_rate * 2.0))
        # Damping factor: q = 1 / Q
        q = 1.0 / self.resonance

        # Step 1
        self.hp = x - self.lp - q * self.bp
        self.bp = self.bp + f * self.hp
        self.lp = self.lp + f * self.bp

        # Step 2 (oversampled)
        self.hp = x - self.lp - q * self.bp
        self.bp = self.bp + f * self.hp
        self.lp = self.lp + f * self.bp

        self.notch = self.hp + self.lp

        return self.lp, self.hp, self.bp, self.notch
