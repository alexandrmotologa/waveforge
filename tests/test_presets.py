"""Tests verifying all built-in factory presets render authentic, non-silent audio."""

import numpy as np
import pytest
from waveforge.graph.presets import PRESET_CATALOG
from waveforge.graph.engine import AudioEngine
from waveforge.graph.patch import NodeGraph


@pytest.mark.parametrize("preset_id", list(PRESET_CATALOG.keys()))
def test_preset_renders_real_audio(preset_id: str):
    """Ensure every built-in preset renders non-silent, finite audio samples."""
    factory = PRESET_CATALOG[preset_id]
    graph = factory()

    assert len(graph.nodes) > 0
    assert len(graph.connections) > 0

    engine = AudioEngine(graph)
    left, right = engine.render(duration_sec=0.25, midi_note=60, velocity=0.85)

    assert len(left) == int(0.25 * graph.sample_rate)
    assert len(right) == int(0.25 * graph.sample_rate)
    assert np.isfinite(left).all(), f"Preset {preset_id} produced NaN or Inf in left channel"
    assert np.isfinite(right).all(), f"Preset {preset_id} produced NaN or Inf in right channel"

    max_left = float(np.max(np.abs(left)))
    max_right = float(np.max(np.abs(right)))
    assert max_left > 1e-4, f"Preset {preset_id} produced silent audio on left channel (peak = {max_left})"
    assert max_right > 1e-4, f"Preset {preset_id} produced silent audio on right channel (peak = {max_right})"


@pytest.mark.parametrize("preset_id", list(PRESET_CATALOG.keys()))
def test_preset_json_roundtrip(preset_id: str):
    """Ensure every preset survives JSON schema export and re-import without loss."""
    graph = PRESET_CATALOG[preset_id]()
    json_data = graph.to_json()
    reloaded = NodeGraph.from_json(json_data)

    assert reloaded.name == graph.name
    assert len(reloaded.nodes) == len(graph.nodes)
    assert len(reloaded.connections) == len(graph.connections)
