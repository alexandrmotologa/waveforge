"""Modular graph abstractions, node execution engine, and preset patches."""

from waveforge.graph.node import (
    BaseNode,
    NodePin,
    OscillatorNode,
    FilterNode,
    ADSRNode,
    VCANode,
    LFONode,
    MixerNode,
    DelayNode,
    DistortionNode,
    ReverbNode,
    PannerNode,
    OutputNode,
    NODE_REGISTRY,
)
from waveforge.graph.patch import NodeConnection, NodeGraph
from waveforge.graph.engine import AudioEngine, midi_to_freq
from waveforge.graph.presets import PRESET_CATALOG, create_acid_303_patch, create_sub_bass_patch, create_lush_pad_patch, create_fm_bell_patch

__all__ = [
    "BaseNode",
    "NodePin",
    "OscillatorNode",
    "FilterNode",
    "ADSRNode",
    "VCANode",
    "LFONode",
    "MixerNode",
    "DelayNode",
    "DistortionNode",
    "ReverbNode",
    "PannerNode",
    "OutputNode",
    "NODE_REGISTRY",
    "NodeConnection",
    "NodeGraph",
    "AudioEngine",
    "midi_to_freq",
    "PRESET_CATALOG",
    "create_acid_303_patch",
    "create_sub_bass_patch",
    "create_lush_pad_patch",
    "create_fm_bell_patch",
]
