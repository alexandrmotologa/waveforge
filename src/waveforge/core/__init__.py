"""Core DSP mathematical algorithms, filters, oscillators, and buffer abstractions."""

from waveforge.core.config import (
    AudioConfig,
    WaveformType,
    FilterType,
    FilterTopology,
    LFOType,
    EnvelopeStage,
    DistortionType,
    PinType,
    PinDirection,
    PinSchema,
    NodeMetadata,
    ConnectionSchema,
    NodeInstanceSchema,
    PatchSchema,
)
from waveforge.core.buffer import AudioBuffer, CircularBuffer
from waveforge.core.oscillators import PolyBLEPOscillator, polyblep_residual
from waveforge.core.filters import BiquadFilter, StateVariableFilter, compute_rbj_coefficients
from waveforge.core.envelopes import ADSREnvelope
from waveforge.core.modulation import LFO, SampleAndHold, EnvelopeFollower
from waveforge.core.effects import DelayEffect, Waveshaper, SchroederReverb, StereoPanner
from waveforge.core.karplus_strong import KarplusStrongString
from waveforge.core.formant import FormantFilter, VOWEL_FORMANTS
from waveforge.core.chorus import StereoChorusEffect
from waveforge.core.percussion import Kick808, Snare808, HiHat808
from waveforge.core.sequencer import StepSequencer, SequencerStep

__all__ = [
    "AudioConfig",
    "WaveformType",
    "FilterType",
    "FilterTopology",
    "LFOType",
    "EnvelopeStage",
    "DistortionType",
    "PinType",
    "PinDirection",
    "PinSchema",
    "NodeMetadata",
    "ConnectionSchema",
    "NodeInstanceSchema",
    "PatchSchema",
    "AudioBuffer",
    "CircularBuffer",
    "PolyBLEPOscillator",
    "polyblep_residual",
    "BiquadFilter",
    "StateVariableFilter",
    "compute_rbj_coefficients",
    "ADSREnvelope",
    "LFO",
    "SampleAndHold",
    "EnvelopeFollower",
    "DelayEffect",
    "Waveshaper",
    "SchroederReverb",
    "StereoPanner",
    "KarplusStrongString",
    "FormantFilter",
    "VOWEL_FORMANTS",
    "StereoChorusEffect",
    "Kick808",
    "Snare808",
    "HiHat808",
    "StepSequencer",
    "SequencerStep",
]
