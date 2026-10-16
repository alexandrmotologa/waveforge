"""Tests for AudioEngine DSP evaluation and preset patch rendering."""

import numpy as np
import pytest
from waveforge.graph.patch import NodeGraph
from waveforge.graph.engine import AudioEngine
from waveforge.graph.presets import PRESET_CATALOG


def test_engine_render_sound():
    g = NodeGraph()
    g.add_node("oscillator", "osc", params={"frequency": 440.0, "waveform": "saw"})
    g.add_node("audio_output", "out", params={"master_volume": 0.8})
    g.connect("osc", "out", "out", "left")

    engine = AudioEngine(g)
    left, right = engine.render(duration_sec=0.1, midi_note=69)  # 69 = A440

    assert len(left) == int(44100 * 0.1)
    # Check that audio is generated and not silent
    peak = np.max(np.abs(left))
    assert 0.5 < peak <= 1.0


def test_all_preset_catalog_renders():
    for name, factory in PRESET_CATALOG.items():
        g = factory()
        engine = AudioEngine(g)
        left, right = engine.render(duration_sec=0.05, midi_note=60)
        assert len(left) > 0
        assert not np.isnan(left).any(), f"NaN in preset {name}"
        assert not np.isinf(left).any(), f"Inf in preset {name}"
