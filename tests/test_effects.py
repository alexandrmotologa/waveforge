"""Tests for delay, waveshaper distortion, and reverb effects."""

import math
import numpy as np
import pytest
from waveforge.core.config import DistortionType
from waveforge.core.effects import DelayEffect, Waveshaper, SchroederReverb, StereoPanner


def test_delay_echo_repetition():
    sr = 44100
    delay_sec = 0.05  # 50ms = 2205 samples
    delay = DelayEffect(sample_rate=sr, delay_time_sec=delay_sec, feedback=0.5, damping=0.0, mix=1.0)

    # Single unit pulse at t=0
    l_out, r_out = delay.process_sample(1.0, 1.0)

    # Read next 2204 samples (should be 0.0)
    for _ in range(2204):
        delay.process_sample(0.0, 0.0)

    # At sample 2205 (50ms), echo arrives
    echo_l, echo_r = delay.process_sample(0.0, 0.0)
    assert abs(echo_l - 1.0) < 0.05
    assert abs(echo_r - 1.0) < 0.05


def test_waveshaper_tanh_saturation():
    shaper = Waveshaper(distortion_type=DistortionType.TANH, drive=5.0, mix=1.0)

    # Input beyond 1.0 should smoothly compress without exceeding 1.0
    out = shaper.process_sample(2.0)
    assert 0.99 < out < 1.0

    # Symmetric behavior around zero
    neg_out = shaper.process_sample(-2.0)
    assert pytest.approx(out) == -neg_out


def test_waveshaper_wavefolder():
    shaper = Waveshaper(distortion_type=DistortionType.FOLD, drive=2.0, mix=1.0)
    # Sine wave folding
    out = shaper.process_sample(1.0)
    assert -1.0 <= out <= 1.0


def test_schroeder_reverb_decay():
    sr = 44100
    rev = SchroederReverb(sample_rate=sr, room_size=0.5, damping=0.2, wet=1.0, dry=0.0)

    # Impulse injection
    rev.process_sample(1.0, 1.0)

    tail_energies = []
    # Collect blocks of reverb tail
    for _ in range(20):
        block_energy = 0.0
        for _ in range(500):
            l, r = rev.process_sample(0.0, 0.0)
            block_energy += l * l + r * r
        tail_energies.append(block_energy)

    # Reverb tail should ring and gradually decay
    assert tail_energies[2] > 0.001
    assert tail_energies[-1] < tail_energies[2]


def test_stereo_panner_equal_power():
    panner = StereoPanner(pan=0.0)  # Center
    l, r = panner.process_sample(1.0, 1.0)
    # At center (angle = pi/4), l = cos(pi/4) ~ 0.707, r = sin(pi/4) ~ 0.707
    assert pytest.approx(l, rel=1e-3) == math.sqrt(0.5)
    assert pytest.approx(r, rel=1e-3) == math.sqrt(0.5)
    # Power conservation: L^2 + R^2 = 1.0
    assert pytest.approx(l * l + r * r, rel=1e-3) == 1.0
