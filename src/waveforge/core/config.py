"""Core configuration, enums, and data schemas for WaveForge DSP."""

from __future__ import annotations
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator


class WaveformType(str, Enum):
    SINE = "sine"
    SAW = "saw"
    SQUARE = "square"
    TRIANGLE = "triangle"
    NOISE = "noise"


class FilterType(str, Enum):
    LOWPASS = "lowpass"
    HIGHPASS = "highpass"
    BANDPASS = "bandpass"
    NOTCH = "notch"
    PEAK = "peak"
    LOW_SHELF = "low_shelf"
    HIGH_SHELF = "high_shelf"
    ALLPASS = "allpass"


class FilterTopology(str, Enum):
    BIQUAD_DF2T = "biquad_df2t"  # Direct Form II Transposed
    BIQUAD_DF1 = "biquad_df1"    # Direct Form I
    SVF_CHAMBERLIN = "svf_chamberlin"  # Chamberlin State Variable Filter


class LFOType(str, Enum):
    SINE = "sine"
    TRIANGLE = "triangle"
    SAW_UP = "saw_up"
    SAW_DOWN = "saw_down"
    SQUARE = "square"
    SAMPLE_HOLD = "sample_hold"


class EnvelopeStage(str, Enum):
    IDLE = "idle"
    ATTACK = "attack"
    DECAY = "decay"
    SUSTAIN = "sustain"
    RELEASE = "release"


class DistortionType(str, Enum):
    TANH = "tanh"
    HARD_CLIP = "hard_clip"
    CUBIC = "cubic"
    DIODE = "diode"
    FOLD = "fold"


class PinType(str, Enum):
    AUDIO = "audio"       # Audio-rate signal (-1.0 to 1.0 nominally)
    CONTROL = "control"   # Control voltage / modulation signal
    PARAMETER = "param"   # Static or stepped parameter


class PinDirection(str, Enum):
    INPUT = "input"
    OUTPUT = "output"


class AudioConfig(BaseModel):
    """Global audio engine settings."""
    sample_rate: int = Field(default=44100, description="Sampling rate in Hz")
    block_size: int = Field(default=128, description="Processing buffer block size in samples")
    channels: int = Field(default=2, description="Channel count: 1 for mono, 2 for stereo")
    bit_depth: int = Field(default=16, description="WAV export bit depth: 16, 24, or 32")

    @field_validator("sample_rate")
    @classmethod
    def validate_sample_rate(cls, v: int) -> int:
        valid_rates = {22050, 32000, 44100, 48000, 88200, 96000, 192000}
        if v not in valid_rates:
            raise ValueError(f"Sample rate {v} must be one of {sorted(valid_rates)}")
        return v

    @field_validator("block_size")
    @classmethod
    def validate_block_size(cls, v: int) -> int:
        if v < 16 or v > 4096 or (v & (v - 1)) != 0:
            raise ValueError(f"Block size {v} must be a power of 2 between 16 and 4096")
        return v

    @field_validator("channels")
    @classmethod
    def validate_channels(cls, v: int) -> int:
        if v not in (1, 2):
            raise ValueError(f"Channels must be 1 (mono) or 2 (stereo), got {v}")
        return v

    @field_validator("bit_depth")
    @classmethod
    def validate_bit_depth(cls, v: int) -> int:
        if v not in (16, 24, 32):
            raise ValueError(f"Bit depth must be 16, 24, or 32, got {v}")
        return v


class PinSchema(BaseModel):
    """Definition of an input or output connection pin on a DSP node."""
    name: str
    pin_type: PinType = PinType.AUDIO
    direction: PinDirection
    default_value: float = 0.0
    min_value: float = -1.0
    max_value: float = 1.0
    unit: str = ""
    description: str = ""


class NodeMetadata(BaseModel):
    """Metadata schema defining a registered DSP node type."""
    type_id: str
    display_name: str
    category: str
    description: str
    inputs: List[PinSchema] = Field(default_factory=list)
    outputs: List[PinSchema] = Field(default_factory=list)
    default_params: Dict[str, Any] = Field(default_factory=dict)


class ConnectionSchema(BaseModel):
    """Directed connection edge between two node pins."""
    from_node: str
    from_pin: str
    to_node: str
    to_pin: str


class NodeInstanceSchema(BaseModel):
    """Serialized node instance inside a patch."""
    id: str
    type_id: str
    x: float = 0.0
    y: float = 0.0
    params: Dict[str, Any] = Field(default_factory=dict)


class PatchSchema(BaseModel):
    """Complete modular synthesizer patch graph."""
    name: str = "Untitled Patch"
    author: str = "WaveForge"
    version: str = "0.1.0"
    sample_rate: int = 44100
    block_size: int = 128
    tempo: float = 120.0
    nodes: List[NodeInstanceSchema] = Field(default_factory=list)
    connections: List[ConnectionSchema] = Field(default_factory=list)
