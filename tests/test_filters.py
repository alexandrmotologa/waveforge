"""Tests for Robert Bristow-Johnson Biquad and Chamberlin SVF filters."""

import math
import numpy as np
import pytest
from waveforge.core.config import FilterType
from waveforge.core.filters import (
    BiquadFilter,
    compute_rbj_coefficients,
    StateVariableFilter,
)


def test_rbj_lowpass_attenuation():
    sr = 44100
    cutoff = 500.0
    flt = BiquadFilter(sample_rate=sr, filter_type=FilterType.LOWPASS, cutoff_hz=cutoff, q=0.7071)

    # Test with low frequency (100 Hz) vs high frequency (5000 Hz)
    t = np.linspace(0, 0.1, int(sr * 0.1), endpoint=False)
    low_freq_sig = np.sin(2.0 * np.pi * 100.0 * t).astype(np.float32)
    high_freq_sig = np.sin(2.0 * np.pi * 5000.0 * t).astype(np.float32)

    flt.reset_state()
    out_low = flt.process_block(low_freq_sig)
    rms_low = np.sqrt(np.mean(out_low[500:] ** 2))

    flt.reset_state()
    out_high = flt.process_block(high_freq_sig)
    rms_high = np.sqrt(np.mean(out_high[500:] ** 2))

    # Low frequency must pass through (~0.707 RMS) while high frequency must be heavily attenuated (>20 dB)
    assert rms_low > 0.6
    assert rms_high < 0.05
    assert rms_low / rms_high > 10.0


def test_rbj_highpass_attenuation():
    sr = 44100
    cutoff = 2000.0
    flt = BiquadFilter(sample_rate=sr, filter_type=FilterType.HIGHPASS, cutoff_hz=cutoff, q=0.7071)

    t = np.linspace(0, 0.1, int(sr * 0.1), endpoint=False)
    low_freq_sig = np.sin(2.0 * np.pi * 100.0 * t).astype(np.float32)
    high_freq_sig = np.sin(2.0 * np.pi * 8000.0 * t).astype(np.float32)

    flt.reset_state()
    out_low = flt.process_block(low_freq_sig)
    rms_low = np.sqrt(np.mean(out_low[500:] ** 2))

    flt.reset_state()
    out_high = flt.process_block(high_freq_sig)
    rms_high = np.sqrt(np.mean(out_high[500:] ** 2))

    # Low frequency must be attenuated, high frequency must pass
    assert rms_high > 0.6
    assert rms_low < 0.05


def test_filter_stability_impulse_response():
    sr = 44100
    for ft in [FilterType.LOWPASS, FilterType.HIGHPASS, FilterType.BANDPASS, FilterType.NOTCH]:
        flt = BiquadFilter(sample_rate=sr, filter_type=ft, cutoff_hz=1000.0, q=5.0)
        # Unit impulse
        impulse = np.zeros(2048, dtype=np.float32)
        impulse[0] = 1.0

        resp = flt.process_block(impulse)
        # Must not explode or contain NaN/Inf
        assert not np.isnan(resp).any()
        assert not np.isinf(resp).any()
        # Impulse response must decay back to near zero
        assert abs(float(resp[-1])) < 1e-3


def test_chamberlin_svf():
    sr = 44100
    svf = StateVariableFilter(sample_rate=sr, cutoff_hz=1000.0, resonance=1.5)

    lp, hp, bp, notch = svf.process_sample(1.0)
    assert not math.isnan(lp)
    assert not math.isnan(hp)
    assert not math.isnan(bp)
    assert not math.isnan(notch)
