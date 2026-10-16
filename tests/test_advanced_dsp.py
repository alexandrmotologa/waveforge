"""Unit tests for advanced DSP algorithms: Karplus-Strong, Formant, Chorus, 808 Drums, and Sequencer."""

import math
import numpy as np
import pytest
from waveforge.core.karplus_strong import KarplusStrongString
from waveforge.core.formant import FormantFilter, VOWEL_FORMANTS
from waveforge.core.chorus import StereoChorusEffect
from waveforge.core.percussion import Kick808, Snare808, HiHat808
from waveforge.core.sequencer import StepSequencer, SequencerStep
from waveforge.graph.node import (
    KarplusStrongNode,
    FormantNode,
    ChorusNode,
    KickNode,
    SnareNode,
    HiHatNode,
    SequencerNode,
    RingModNode,
)


def test_karplus_strong_plucked_string():
    """Verify Karplus-Strong acoustic string physical modeling loop."""
    sr = 44100
    ks = KarplusStrongString(sample_rate=sr, frequency=440.0, decay=0.98, damping=0.3)
    ks.trigger_pluck(velocity=1.0)

    # Process 1 second of audio
    block = ks.process_block(sr)
    assert len(block) == sr
    assert np.isfinite(block).all()

    # Initial pluck transient should have strong energy
    initial_energy = np.mean(block[:500] ** 2)
    # Tail should decay exponentially
    tail_energy = np.mean(block[-2000:] ** 2)
    assert initial_energy > 1e-4
    assert tail_energy < initial_energy * 0.1
    # Check bounded within [-1.0, 1.0]
    assert np.max(np.abs(block)) <= 1.05


def test_formant_vowel_filter():
    """Verify triple-peak formant vocal resonator with phoneme morphing."""
    sr = 44100
    filt = FormantFilter(sample_rate=sr, vowel_pos=0.0)  # Vowel 'A'

    # Excite with rich impulse train / saw wave
    t = np.linspace(0, 0.1, int(sr * 0.1), endpoint=False)
    saw = 2.0 * (t * 130.0 - np.floor(t * 130.0 + 0.5))

    out_a = filt.process_block(saw.astype(np.float32))
    assert np.isfinite(out_a).all()
    assert np.max(np.abs(out_a)) > 0.01

    # Switch to 'I'
    filt.set_vowel(2.0)
    out_i = filt.process_block(saw.astype(np.float32))
    assert np.isfinite(out_i).all()
    # Different vowels must produce distinct spectra and waveforms
    diff = np.mean(np.abs(out_a - out_i))
    assert diff > 0.005


def test_stereo_bbd_chorus():
    """Verify stereo BBD chorus effect with 90-degree quadrature modulation."""
    sr = 44100
    chorus = StereoChorusEffect(sample_rate=sr, rate_hz=1.5, depth_ms=4.0, mix=0.5)

    # Sine wave mono input
    t = np.arange(1024) / sr
    mono = np.sin(2.0 * np.pi * 440.0 * t).astype(np.float32)

    out_l = np.zeros(1024, dtype=np.float32)
    out_r = np.zeros(1024, dtype=np.float32)

    for i in range(1024):
        ol, or_val = chorus.process_sample(mono[i], mono[i])
        out_l[i] = ol
        out_r[i] = or_val

    assert np.isfinite(out_l).all()
    assert np.isfinite(out_r).all()
    # Left and right channels must diverge due to 90 deg quadrature phase shift
    assert not np.allclose(out_l[200:], out_r[200:], atol=1e-4)


def test_tr808_kick():
    """Verify analog 808 kick drum exponential pitch dive and saturation."""
    sr = 44100
    kick = Kick808(sample_rate=sr, pitch_start=220.0, pitch_end=48.0, decay_time=0.4)
    kick.trigger(velocity=1.0)

    samples = [kick.process_sample() for _ in range(int(sr * 0.5))]
    arr = np.array(samples, dtype=np.float32)

    assert np.isfinite(arr).all()
    # Peak amplitude should be prominent
    assert np.max(np.abs(arr)) > 0.4
    # Bounded by soft saturation
    assert np.max(np.abs(arr)) <= 1.0


def test_tr808_snare():
    """Verify analog 808 snare dual body tone and bandpass snappy noise."""
    sr = 44100
    snare = Snare808(sample_rate=sr, tone_freq=180.0, snappy_mix=0.7)
    snare.trigger(velocity=1.0)

    samples = [snare.process_sample() for _ in range(int(sr * 0.4))]
    arr = np.array(samples, dtype=np.float32)

    assert np.isfinite(arr).all()
    assert np.max(np.abs(arr)) > 0.3
    assert np.max(np.abs(arr)) <= 1.0


def test_tr808_hihat():
    """Verify 6-oscillator metallic cluster and resonant highpass decay."""
    sr = 44100
    hat = HiHat808(sample_rate=sr, decay_time=0.05, cutoff_hz=7000.0)

    # Closed hat
    hat.trigger(velocity=1.0, open_hat=False)
    closed_samples = [hat.process_sample() for _ in range(int(sr * 0.2))]
    closed_arr = np.array(closed_samples, dtype=np.float32)

    # Open hat
    hat.trigger(velocity=1.0, open_hat=True)
    open_samples = [hat.process_sample() for _ in range(int(sr * 0.5))]
    open_arr = np.array(open_samples, dtype=np.float32)

    assert np.isfinite(closed_arr).all()
    assert np.isfinite(open_arr).all()
    # Open hat must ring longer than closed hat
    closed_tail = np.mean(closed_arr[int(sr * 0.1):] ** 2)
    open_tail = np.mean(open_arr[int(sr * 0.1):int(sr * 0.2)] ** 2)
    assert open_tail > closed_tail


def test_16_step_sequencer():
    """Verify 16-step sequencer timing, 303 portamento slide, and gate dynamics."""
    sr = 44100
    seq = StepSequencer(sample_rate=sr, bpm=120.0, gate_length=0.5, slide_time=0.05)

    # At 120 BPM: 2 beats/sec -> 8 steps/sec -> 44100 / 8 = 5512.5 samples per step
    step_samples = seq.samples_per_step()
    assert 5510 <= step_samples <= 5515

    pitches = []
    gates = []
    for _ in range(step_samples * 4):
        p, g, a = seq.process_sample()
        pitches.append(p)
        gates.append(g)

    p_arr = np.array(pitches)
    g_arr = np.array(gates)

    assert np.isfinite(p_arr).all()
    assert np.isfinite(g_arr).all()
    # Gates should toggle between active (> 0) and inactive (== 0)
    assert np.any(g_arr > 0)
    assert np.any(g_arr == 0)


def test_ring_modulator_node():
    """Verify audio-rate four-quadrant multiplier produces sum and difference sidebands."""
    sr = 44100
    rm = RingModNode("rm1", sample_rate=sr, params={"mix": 1.0})

    # Carrier 440 Hz, Modulator 100 Hz
    t = np.arange(256) / sr
    car = np.sin(2.0 * np.pi * 440.0 * t).astype(np.float32)
    mod = np.sin(2.0 * np.pi * 100.0 * t).astype(np.float32)

    res = rm.process(256, inputs={"carrier": car, "modulator": mod})
    out = res["out"]

    assert len(out) == 256
    assert np.isfinite(out).all()
    expected = car * mod
    assert np.allclose(out, expected, atol=1e-5)
