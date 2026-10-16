"""Tests for WaveForge core configuration, validation, and schemas."""

import pytest
from waveforge.core.config import (
    AudioConfig,
    WaveformType,
    FilterType,
    PinType,
    PinDirection,
    PinSchema,
    NodeMetadata,
    ConnectionSchema,
    NodeInstanceSchema,
    PatchSchema,
)


def test_audio_config_defaults():
    cfg = AudioConfig()
    assert cfg.sample_rate == 44100
    assert cfg.block_size == 128
    assert cfg.channels == 2
    assert cfg.bit_depth == 16


def test_audio_config_validation():
    # Valid
    cfg = AudioConfig(sample_rate=48000, block_size=256, channels=1, bit_depth=24)
    assert cfg.sample_rate == 48000
    assert cfg.block_size == 256

    # Invalid sample rate
    with pytest.raises(ValueError):
        AudioConfig(sample_rate=12345)

    # Invalid block size (not power of 2)
    with pytest.raises(ValueError):
        AudioConfig(block_size=100)

    # Invalid channels
    with pytest.raises(ValueError):
        AudioConfig(channels=5)


def test_patch_schema_serialization():
    patch = PatchSchema(
        name="Test Patch",
        sample_rate=44100,
        nodes=[
            NodeInstanceSchema(id="osc1", type_id="oscillator", params={"frequency": 440.0}),
            NodeInstanceSchema(id="out1", type_id="audio_output", params={}),
        ],
        connections=[
            ConnectionSchema(from_node="osc1", from_pin="out", to_node="out1", to_pin="left")
        ],
    )
    json_str = patch.model_dump_json()
    assert "Test Patch" in json_str
    reconstructed = PatchSchema.model_validate_json(json_str)
    assert reconstructed.name == "Test Patch"
    assert len(reconstructed.nodes) == 2
    assert len(reconstructed.connections) == 1
