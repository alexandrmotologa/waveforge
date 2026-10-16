"""Tests for PolyBLEP anti-aliased oscillators and residual equations."""

import math
import numpy as np
import pytest
from waveforge.core.config import WaveformType
from waveforge.core.oscillators import (
    PolyBLEPOscillator,
    polyblep_residual,
    polyblamp_residual,
)


def test_polyblep_residual_boundaries():
    dt = 0.05

    # Center of cycle should have zero residual
    assert polyblep_residual(0.5, dt) == 0.0
    assert polyblep_residual(0.2, dt) == 0.0

    # At t=0 (x=0), r = -1.0
    assert pytest.approx(polyblep_residual(0.0, dt), 1e-4) == -1.0

    # At t=dt (x=1), r = 2(1) - 1^2 - 1 = 0.0
    assert pytest.approx(polyblep_residual(dt, dt), 1e-4) == 0.0

    # At t -> 1 (near end of cycle)
    r_near_1 = polyblep_residual(1.0 - 0.5 * dt, dt)
    assert r_near_1 != 0.0


def test_oscillator_sine_purity():
    sr = 44100
    freq = 441.0  # Exactly 100 samples per period
    osc = PolyBLEPOscillator(sample_rate=sr, frequency=freq, waveform=WaveformType.SINE)

    block = osc.process_block(100)
    # Sine max should be 1.0, min should be -1.0, mean near 0
    assert pytest.approx(float(np.max(block)), rel=1e-2) == 1.0
    assert pytest.approx(float(np.min(block)), rel=1e-2) == -1.0
    assert abs(float(np.mean(block))) < 0.05


def test_oscillator_saw_polyblep():
    sr = 44100
    freq = 440.0
    osc = PolyBLEPOscillator(sample_rate=sr, frequency=freq, waveform=WaveformType.SAW)

    block = osc.process_block(1024)
    # Output must stay cleanly bounded within [-1.1, 1.1]
    assert np.all(block >= -1.1)
    assert np.all(block <= 1.1)
    # RMS of sawtooth wave is 1 / sqrt(3) ~ 0.577
    rms = float(np.sqrt(np.mean(block ** 2)))
    assert 0.5 < rms < 0.65


def test_oscillator_square_pulse_width():
    sr = 44100
    freq = 220.0
    osc = PolyBLEPOscillator(sample_rate=sr, frequency=freq, waveform=WaveformType.SQUARE, pulse_width=0.5)

    block = osc.process_block(800)
    assert np.all(block >= -1.1)
    assert np.all(block <= 1.1)
    # 50% duty cycle should have near zero mean
    assert abs(float(np.mean(block))) < 0.05

    # Asymmetric pulse width 25%
    osc.set_pulse_width(0.25)
    block_pw = osc.process_block(2000)
    # 25% duty cycle: expected DC mean = 0.25*(1) + 0.75*(-1) = -0.5
    assert abs(float(np.mean(block_pw)) - (-0.5)) < 0.1


def test_oscillator_triangle():
    sr = 44100
    freq = 440.0
    osc = PolyBLEPOscillator(sample_rate=sr, frequency=freq, waveform=WaveformType.TRIANGLE)

    block = osc.process_block(2000)
    # Discard warmup
    steady = block[1000:]
    assert np.all(steady >= -1.05)
    assert np.all(steady <= 1.05)
    assert abs(float(np.mean(steady))) < 0.08


def test_oscillator_noise():
    sr = 44100
    osc = PolyBLEPOscillator(sample_rate=sr, waveform=WaveformType.NOISE)

    block = osc.process_block(4096)
    # Noise should be non-zero and bounded
    assert float(np.std(block)) > 0.05
    assert np.all(block >= -1.5)
    assert np.all(block <= 1.5)
