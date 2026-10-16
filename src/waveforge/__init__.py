"""WaveForge: Modular audio DSP engine, visual node synthesizer, and C/Wasm code generator."""

__version__ = "0.1.0"
__author__ = "Alexandr Motologa"

from waveforge.core.config import AudioConfig, WaveformType, FilterType
from waveforge.core.oscillators import PolyBLEPOscillator
from waveforge.core.filters import BiquadFilter, StateVariableFilter
from waveforge.core.envelopes import ADSREnvelope
from waveforge.graph.patch import NodeGraph
from waveforge.graph.engine import AudioEngine

__all__ = [
    "AudioConfig",
    "WaveformType",
    "FilterType",
    "PolyBLEPOscillator",
    "BiquadFilter",
    "StateVariableFilter",
    "ADSREnvelope",
    "NodeGraph",
    "AudioEngine",
]
