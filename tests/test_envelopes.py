"""Tests for analog-modeled exponential ADSR envelope generators."""

import numpy as np
import pytest
from waveforge.core.config import EnvelopeStage
from waveforge.core.envelopes import ADSREnvelope


def test_adsr_stages_progression():
    sr = 44100
    attack = 0.01   # ~441 samples
    decay = 0.02    # ~882 samples
    sustain = 0.5
    release = 0.02  # ~882 samples

    env = ADSREnvelope(sample_rate=sr, attack=attack, decay=decay, sustain=sustain, release=release)
    assert env.stage == EnvelopeStage.IDLE

    # Trigger Gate On
    env.gate_on()
    assert env.stage == EnvelopeStage.ATTACK

    # Process samples until peak reached
    vals = []
    for _ in range(int(attack * sr * 2)):
        v = env.process_sample()
        vals.append(v)
        if env.stage == EnvelopeStage.DECAY:
            break

    assert env.stage == EnvelopeStage.DECAY
    # Max value reached 1.0
    assert pytest.approx(max(vals), rel=1e-2) == 1.0

    # Process decay into sustain
    for _ in range(int(decay * sr * 3)):
        v = env.process_sample()
        if env.stage == EnvelopeStage.SUSTAIN:
            break

    assert env.stage == EnvelopeStage.SUSTAIN
    assert pytest.approx(env.current_value, rel=1e-2) == sustain

    # Trigger Gate Off (Release)
    env.gate_off()
    assert env.stage == EnvelopeStage.RELEASE

    # Process until Idle
    for _ in range(int(release * sr * 4)):
        v = env.process_sample()
        if env.stage == EnvelopeStage.IDLE:
            break

    assert env.stage == EnvelopeStage.IDLE
    assert env.current_value == 0.0
