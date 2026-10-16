"""Authentic audio DSP effects: Delay, Waveshaper/Distortion, Schroeder Reverb, and Panner."""

from __future__ import annotations
import math
import numpy as np
from typing import Tuple, Optional
from waveforge.core.config import DistortionType
from waveforge.core.buffer import CircularBuffer
from waveforge.core.filters import BiquadFilter, FilterType


class DelayEffect:
    """Stereo ping-pong / tape delay with feedback damping and fractional interpolation."""

    def __init__(
        self,
        sample_rate: int = 44100,
        delay_time_sec: float = 0.35,
        feedback: float = 0.4,
        damping: float = 0.2,   # High-frequency damping in feedback loop
        mix: float = 0.3,
        ping_pong: bool = False,
    ):
        self.sample_rate = float(sample_rate)
        self.delay_time_sec = max(0.001, min(float(delay_time_sec), 2.0))
        self.feedback = max(0.0, min(float(feedback), 0.98))
        self.damping = max(0.0, min(float(damping), 0.95))
        self.mix = max(0.0, min(float(mix), 1.0))
        self.ping_pong = ping_pong

        # Max 2.5 seconds circular buffer
        max_samples = int(self.sample_rate * 2.5)
        self.buffer = CircularBuffer(max_samples, channels=2)

        # One-pole damping filters in feedback loop
        self._damp_l = 0.0
        self._damp_r = 0.0

    def set_sample_rate(self, sr: int) -> None:
        self.sample_rate = float(sr)
        max_samples = int(self.sample_rate * 2.5)
        self.buffer = CircularBuffer(max_samples, channels=2)
        self._damp_l = 0.0
        self._damp_r = 0.0

    def process_sample(self, in_l: float, in_r: float) -> Tuple[float, float]:
        delay_samples = self.delay_time_sec * self.sample_rate

        # Read delayed samples with Hermite interpolation
        delayed_l = self.buffer.read_sample_hermite(delay_samples, channel=0)
        delayed_r = self.buffer.read_sample_hermite(delay_samples, channel=1)

        # Apply lowpass damping in feedback path: y = (1-d)*x + d*y_prev
        self._damp_l = (1.0 - self.damping) * delayed_l + self.damping * self._damp_l
        self._damp_r = (1.0 - self.damping) * delayed_r + self.damping * self._damp_r

        # Calculate feedback injection
        if self.ping_pong:
            # Cross feedback channels
            fb_l = in_l + self._damp_r * self.feedback
            fb_r = in_r + self._damp_l * self.feedback
        else:
            fb_l = in_l + self._damp_l * self.feedback
            fb_r = in_r + self._damp_r * self.feedback

        # Soft clip feedback to prevent catastrophic runaway if exceeding unity
        if abs(fb_l) > 1.0:
            fb_l = math.tanh(fb_l)
        if abs(fb_r) > 1.0:
            fb_r = math.tanh(fb_r)

        self.buffer.write_sample([fb_l, fb_r])

        # Mix dry and wet
        dry = 1.0 - self.mix
        wet = self.mix
        out_l = dry * in_l + wet * delayed_l
        out_r = dry * in_r + wet * delayed_r

        return out_l, out_r


class Waveshaper:
    """Non-linear saturation, diode overdrive, and wavefolding distortion."""

    def __init__(
        self,
        distortion_type: DistortionType = DistortionType.TANH,
        drive: float = 2.0,
        mix: float = 1.0,
    ):
        self.distortion_type = distortion_type
        self.drive = max(0.1, min(float(drive), 50.0))
        self.mix = max(0.0, min(float(mix), 1.0))
        self._dc_state = 0.0

    def process_sample(self, x: float) -> float:
        d = self.drive
        shaped = 0.0

        if self.distortion_type == DistortionType.TANH:
            # Smooth tube/tape saturation
            shaped = math.tanh(d * x)

        elif self.distortion_type == DistortionType.HARD_CLIP:
            v = d * x
            shaped = max(-1.0, min(1.0, v))

        elif self.distortion_type == DistortionType.CUBIC:
            # Soft symmetrical clipping: x - x^3 / 3
            v = max(-1.5, min(1.5, d * x * (2.0 / 3.0)))
            shaped = v - (v * v * v) / 3.0

        elif self.distortion_type == DistortionType.DIODE:
            # Asymmetrical diode curve + DC blocking
            v = d * x
            if v > 0:
                shaped = 1.0 - math.exp(-v)
            else:
                shaped = -0.3 * (1.0 - math.exp(v))
            # Leaky highpass DC blocker
            shaped_clean = shaped - self._dc_state
            self._dc_state = shaped - 0.995 * shaped_clean
            shaped = shaped_clean

        elif self.distortion_type == DistortionType.FOLD:
            # Buchla-style wavefolder
            v = d * x
            shaped = math.sin(v * math.pi * 0.5)

        # Mix dry and wet
        dry = 1.0 - self.mix
        return dry * x + self.mix * shaped


class CombFilter:
    """Feedback comb filter with lowpass damping in feedback path."""

    def __init__(self, size: int):
        self.size = size
        self.buffer = np.zeros(size, dtype=np.float32)
        self.idx = 0
        self.filter_state = 0.0

    def process(self, x: float, feedback: float, damping: float) -> float:
        out = self.buffer[self.idx]
        self.filter_state = out * (1.0 - damping) + self.filter_state * damping
        self.buffer[self.idx] = x + self.filter_state * feedback
        self.idx = (self.idx + 1) % self.size
        return out


class AllpassFilter:
    """Schroeder allpass filter providing diffuse phase dispersion."""

    def __init__(self, size: int):
        self.size = size
        self.buffer = np.zeros(size, dtype=np.float32)
        self.idx = 0

    def process(self, x: float, feedback: float = 0.5) -> float:
        buf_out = self.buffer[self.idx]
        out = -x + buf_out
        self.buffer[self.idx] = x + buf_out * feedback
        self.idx = (self.idx + 1) % self.size
        return out


class SchroederReverb:
    """Schroeder-Moorer digital reverberator (Freeverb topology).

    Uses 8 parallel feedback comb filters followed by 4 series allpass diffusors.
    """

    # Standard Freeverb comb filter tuning delays (in samples at 44.1 kHz)
    COMB_TUNINGS = [1116, 1188, 1277, 1356, 1422, 1491, 1557, 1617]
    ALLPASS_TUNINGS = [556, 441, 341, 225]
    STEREO_SPREAD = 23

    def __init__(
        self,
        sample_rate: int = 44100,
        room_size: float = 0.5,
        damping: float = 0.5,
        wet: float = 0.33,
        dry: float = 0.67,
        width: float = 1.0,
    ):
        self.sample_rate = float(sample_rate)
        self.room_size = float(room_size)
        self.damping = float(damping)
        self.wet = float(wet)
        self.dry = float(dry)
        self.width = float(width)

        self._build_filters()

    def _build_filters(self) -> None:
        sr_scale = self.sample_rate / 44100.0

        self.combs_l = [
            CombFilter(max(1, int(t * sr_scale))) for t in self.COMB_TUNINGS
        ]
        self.combs_r = [
            CombFilter(max(1, int((t + self.STEREO_SPREAD) * sr_scale)))
            for t in self.COMB_TUNINGS
        ]

        self.allpass_l = [
            AllpassFilter(max(1, int(t * sr_scale))) for t in self.ALLPASS_TUNINGS
        ]
        self.allpass_r = [
            AllpassFilter(max(1, int((t + self.STEREO_SPREAD) * sr_scale)))
            for t in self.ALLPASS_TUNINGS
        ]

    def set_sample_rate(self, sr: int) -> None:
        self.sample_rate = float(sr)
        self._build_filters()

    def process_sample(self, in_l: float, in_r: float) -> Tuple[float, float]:
        # Scale parameters
        # Feedback between 0.7 and 0.98
        feedback = 0.7 + self.room_size * 0.28
        # Damping between 0.0 and 0.4
        damping = self.damping * 0.4

        mono_in = (in_l + in_r) * 0.5

        out_l = 0.0
        out_r = 0.0

        # Accumulate 8 parallel comb filters
        for c_l, c_r in zip(self.combs_l, self.combs_r):
            out_l += c_l.process(mono_in, feedback, damping)
            out_r += c_r.process(mono_in, feedback, damping)

        # Pass through 4 series allpass filters
        for ap_l, ap_r in zip(self.allpass_l, self.allpass_r):
            out_l = ap_l.process(out_l, 0.5)
            out_r = ap_r.process(out_r, 0.5)

        # Stereo width adjustment
        wet1 = self.wet * (self.width * 0.5 + 0.5)
        wet2 = self.wet * ((1.0 - self.width) * 0.5)

        res_l = out_l * wet1 + out_r * wet2 + in_l * self.dry
        res_r = out_r * wet1 + out_l * wet2 + in_r * self.dry

        return res_l, res_r


class StereoPanner:
    """Constant-power stereo panner using sine-cosine equal-power law."""

    def __init__(self, pan: float = 0.0):
        # pan in [-1.0, 1.0]: -1.0 = full left, 0.0 = center, 1.0 = full right
        self.pan = max(-1.0, min(1.0, float(pan)))

    def process_sample(self, in_l: float, in_r: float, pan_mod: float = 0.0) -> Tuple[float, float]:
        p = max(-1.0, min(1.0, self.pan + pan_mod))
        # Equal power angle in [0, pi/2]
        angle = (p + 1.0) * (math.pi * 0.25)
        gain_l = math.cos(angle)
        gain_r = math.sin(angle)
        return in_l * gain_l, in_r * gain_r
