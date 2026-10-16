"""Base Node abstractions and concrete DSP nodes for the modular synthesizer graph."""

from __future__ import annotations
import math
import numpy as np
from typing import Dict, List, Any, Optional
from waveforge.core.config import (
    PinType,
    PinDirection,
    PinSchema,
    NodeMetadata,
    WaveformType,
    FilterType,
    LFOType,
    DistortionType,
)
from waveforge.core.oscillators import PolyBLEPOscillator
from waveforge.core.filters import BiquadFilter, StateVariableFilter
from waveforge.core.envelopes import ADSREnvelope
from waveforge.core.modulation import LFO
from waveforge.core.effects import DelayEffect, Waveshaper, SchroederReverb, StereoPanner
from waveforge.core.karplus_strong import KarplusStrongString
from waveforge.core.formant import FormantFilter
from waveforge.core.chorus import StereoChorusEffect
from waveforge.core.percussion import Kick808, Snare808, HiHat808
from waveforge.core.sequencer import StepSequencer, SequencerStep


class NodePin:
    """Represents an input or output terminal on a DSP node."""

    def __init__(self, schema: PinSchema):
        self.schema = schema
        self.name = schema.name
        self.pin_type = schema.pin_type
        self.direction = schema.direction
        self.default_value = schema.default_value


class BaseNode:
    """Abstract base class for all processing units in the modular graph."""

    TYPE_ID: str = "base"
    DISPLAY_NAME: str = "Base Node"
    CATEGORY: str = "Utility"
    DESCRIPTION: str = "Base DSP node"

    def __init__(
        self,
        node_id: str,
        sample_rate: int = 44100,
        params: Optional[Dict[str, Any]] = None,
    ):
        self.node_id = node_id
        self.sample_rate = sample_rate
        self.params: Dict[str, Any] = self.get_default_params()
        if params:
            self.params.update(params)

        self.input_pins: Dict[str, NodePin] = {}
        self.output_pins: Dict[str, NodePin] = {}
        self._init_pins()

    @classmethod
    def get_metadata(cls) -> NodeMetadata:
        raise NotImplementedError

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {}

    def _init_pins(self) -> None:
        meta = self.get_metadata()
        for p in meta.inputs:
            self.input_pins[p.name] = NodePin(p)
        for p in meta.outputs:
            self.output_pins[p.name] = NodePin(p)

    def set_sample_rate(self, sr: int) -> None:
        self.sample_rate = sr

    def set_param(self, name: str, value: Any) -> None:
        if name in self.params:
            self.params[name] = value

    def reset_state(self) -> None:
        pass

    def process(
        self,
        block_size: int,
        inputs: Dict[str, np.ndarray],
    ) -> Dict[str, np.ndarray]:
        """Compute block of output samples from block of input samples."""
        raise NotImplementedError


class OscillatorNode(BaseNode):
    """Anti-aliased PolyBLEP oscillator node."""

    TYPE_ID = "oscillator"
    DISPLAY_NAME = "PolyBLEP Oscillator"
    CATEGORY = "Generators"
    DESCRIPTION = "Anti-aliased oscillator producing Saw, Square, Triangle, Sine, and Pink Noise."

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {
            "waveform": "saw",
            "frequency": 220.0,
            "pulse_width": 0.5,
            "phase": 0.0,
        }

    @classmethod
    def get_metadata(cls) -> NodeMetadata:
        return NodeMetadata(
            type_id=cls.TYPE_ID,
            display_name=cls.DISPLAY_NAME,
            category=cls.CATEGORY,
            description=cls.DESCRIPTION,
            inputs=[
                PinSchema(name="freq_mod", pin_type=PinType.CONTROL, direction=PinDirection.INPUT, default_value=0.0, min_value=-2000.0, max_value=2000.0, unit="Hz"),
                PinSchema(name="pm", pin_type=PinType.AUDIO, direction=PinDirection.INPUT, default_value=0.0, min_value=-5.0, max_value=5.0, unit="rad"),
                PinSchema(name="sync", pin_type=PinType.CONTROL, direction=PinDirection.INPUT, default_value=0.0, min_value=0.0, max_value=1.0),
            ],
            outputs=[
                PinSchema(name="out", pin_type=PinType.AUDIO, direction=PinDirection.OUTPUT, default_value=0.0, min_value=-1.0, max_value=1.0),
            ],
            default_params=cls.get_default_params(),
        )

    def __init__(self, node_id: str, sample_rate: int = 44100, params: Optional[Dict[str, Any]] = None):
        super().__init__(node_id, sample_rate, params)
        wf = WaveformType(self.params.get("waveform", "saw"))
        freq = float(self.params.get("frequency", 220.0))
        pw = float(self.params.get("pulse_width", 0.5))
        self.osc = PolyBLEPOscillator(sample_rate, freq, wf, pw)

    def set_sample_rate(self, sr: int) -> None:
        super().set_sample_rate(sr)
        self.osc.set_sample_rate(sr)

    def reset_state(self) -> None:
        self.osc.reset_phase()

    def process(self, block_size: int, inputs: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        wf = WaveformType(self.params.get("waveform", "saw"))
        self.osc.set_waveform(wf)
        self.osc.set_frequency(float(self.params.get("frequency", 220.0)))
        self.osc.set_pulse_width(float(self.params.get("pulse_width", 0.5)))

        fm = inputs.get("freq_mod")
        pm = inputs.get("pm")
        sync = inputs.get("sync")

        out = self.osc.process_block(block_size, freq_mod=fm, phase_mod=pm, sync_triggers=sync)
        return {"out": out}


class FilterNode(BaseNode):
    """Biquad IIR filter node with Audio EQ Cookbook equations."""

    TYPE_ID = "biquad_filter"
    DISPLAY_NAME = "Biquad Filter"
    CATEGORY = "Filters"
    DESCRIPTION = "Multi-mode resonant biquad filter (Lowpass, Highpass, Bandpass, Notch, Peak, Shelves)."

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {
            "filter_type": "lowpass",
            "cutoff_hz": 1200.0,
            "q": 1.5,
            "gain_db": 0.0,
        }

    @classmethod
    def get_metadata(cls) -> NodeMetadata:
        return NodeMetadata(
            type_id=cls.TYPE_ID,
            display_name=cls.DISPLAY_NAME,
            category=cls.CATEGORY,
            description=cls.DESCRIPTION,
            inputs=[
                PinSchema(name="in", pin_type=PinType.AUDIO, direction=PinDirection.INPUT, default_value=0.0, min_value=-1.0, max_value=1.0),
                PinSchema(name="cutoff_mod", pin_type=PinType.CONTROL, direction=PinDirection.INPUT, default_value=0.0, min_value=-5000.0, max_value=5000.0, unit="Hz"),
            ],
            outputs=[
                PinSchema(name="out", pin_type=PinType.AUDIO, direction=PinDirection.OUTPUT, default_value=0.0, min_value=-1.0, max_value=1.0),
            ],
            default_params=cls.get_default_params(),
        )

    def __init__(self, node_id: str, sample_rate: int = 44100, params: Optional[Dict[str, Any]] = None):
        super().__init__(node_id, sample_rate, params)
        ft = FilterType(self.params.get("filter_type", "lowpass"))
        cutoff = float(self.params.get("cutoff_hz", 1200.0))
        q = float(self.params.get("q", 1.5))
        gain = float(self.params.get("gain_db", 0.0))
        self.filter = BiquadFilter(sample_rate, ft, cutoff, q, gain)

    def set_sample_rate(self, sr: int) -> None:
        super().set_sample_rate(sr)
        self.filter.set_sample_rate(sr)

    def reset_state(self) -> None:
        self.filter.reset_state()

    def process(self, block_size: int, inputs: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        ft = FilterType(self.params.get("filter_type", "lowpass"))
        cutoff = float(self.params.get("cutoff_hz", 1200.0))
        q = float(self.params.get("q", 1.5))
        gain = float(self.params.get("gain_db", 0.0))
        self.filter.set_params(ft, cutoff, q, gain)

        in_buf = inputs.get("in", np.zeros(block_size, dtype=np.float32))
        cutoff_mod = inputs.get("cutoff_mod")

        out = self.filter.process_block(in_buf, cutoff_mod=cutoff_mod)
        return {"out": out}


class ADSRNode(BaseNode):
    """Exponential ADSR envelope generator node."""

    TYPE_ID = "adsr"
    DISPLAY_NAME = "ADSR Envelope"
    CATEGORY = "Envelopes"
    DESCRIPTION = "Analog-modeled exponential ADSR envelope generator."

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {
            "attack": 0.01,
            "decay": 0.15,
            "sustain": 0.6,
            "release": 0.25,
        }

    @classmethod
    def get_metadata(cls) -> NodeMetadata:
        return NodeMetadata(
            type_id=cls.TYPE_ID,
            display_name=cls.DISPLAY_NAME,
            category=cls.CATEGORY,
            description=cls.DESCRIPTION,
            inputs=[
                PinSchema(name="gate", pin_type=PinType.CONTROL, direction=PinDirection.INPUT, default_value=0.0, min_value=0.0, max_value=1.0),
            ],
            outputs=[
                PinSchema(name="out", pin_type=PinType.CONTROL, direction=PinDirection.OUTPUT, default_value=0.0, min_value=0.0, max_value=1.0),
            ],
            default_params=cls.get_default_params(),
        )

    def __init__(self, node_id: str, sample_rate: int = 44100, params: Optional[Dict[str, Any]] = None):
        super().__init__(node_id, sample_rate, params)
        a = float(self.params.get("attack", 0.01))
        d = float(self.params.get("decay", 0.15))
        s = float(self.params.get("sustain", 0.6))
        r = float(self.params.get("release", 0.25))
        self.env = ADSREnvelope(sample_rate, a, d, s, r)

    def set_sample_rate(self, sr: int) -> None:
        super().set_sample_rate(sr)
        self.env.set_sample_rate(sr)

    def reset_state(self) -> None:
        self.env.reset()

    def process(self, block_size: int, inputs: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        a = float(self.params.get("attack", 0.01))
        d = float(self.params.get("decay", 0.15))
        s = float(self.params.get("sustain", 0.6))
        r = float(self.params.get("release", 0.25))
        self.env.set_params(a, d, s, r)

        gate_vec = inputs.get("gate")
        out = self.env.process_block(block_size, gate_vector=gate_vec)
        return {"out": out}


class VCANode(BaseNode):
    """Voltage Controlled Amplifier / Signal Multiplier node."""

    TYPE_ID = "vca"
    DISPLAY_NAME = "VCA / Multiplier"
    CATEGORY = "Modulation"
    DESCRIPTION = "Scales input signal amplitude with gain parameter and CV modulation."

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {"gain": 1.0}

    @classmethod
    def get_metadata(cls) -> NodeMetadata:
        return NodeMetadata(
            type_id=cls.TYPE_ID,
            display_name=cls.DISPLAY_NAME,
            category=cls.CATEGORY,
            description=cls.DESCRIPTION,
            inputs=[
                PinSchema(name="in", pin_type=PinType.AUDIO, direction=PinDirection.INPUT, default_value=0.0),
                PinSchema(name="cv", pin_type=PinType.CONTROL, direction=PinDirection.INPUT, default_value=1.0),
            ],
            outputs=[
                PinSchema(name="out", pin_type=PinType.AUDIO, direction=PinDirection.OUTPUT, default_value=0.0),
            ],
            default_params=cls.get_default_params(),
        )

    def process(self, block_size: int, inputs: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        gain = float(self.params.get("gain", 1.0))
        in_buf = inputs.get("in", np.zeros(block_size, dtype=np.float32))
        cv_buf = inputs.get("cv")

        if cv_buf is not None:
            out = in_buf * cv_buf * gain
        else:
            out = in_buf * gain
        return {"out": out}


class LFONode(BaseNode):
    """Low Frequency Oscillator node."""

    TYPE_ID = "lfo"
    DISPLAY_NAME = "LFO"
    CATEGORY = "Modulation"
    DESCRIPTION = "Cyclic modulation oscillator (Sine, Triangle, Saw, Square, Sample & Hold)."

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {
            "rate_hz": 2.5,
            "waveform": "sine",
            "depth": 1.0,
            "bipolar": True,
        }

    @classmethod
    def get_metadata(cls) -> NodeMetadata:
        return NodeMetadata(
            type_id=cls.TYPE_ID,
            display_name=cls.DISPLAY_NAME,
            category=cls.CATEGORY,
            description=cls.DESCRIPTION,
            inputs=[
                PinSchema(name="sync", pin_type=PinType.CONTROL, direction=PinDirection.INPUT, default_value=0.0),
            ],
            outputs=[
                PinSchema(name="out", pin_type=PinType.CONTROL, direction=PinDirection.OUTPUT, default_value=0.0),
            ],
            default_params=cls.get_default_params(),
        )

    def __init__(self, node_id: str, sample_rate: int = 44100, params: Optional[Dict[str, Any]] = None):
        super().__init__(node_id, sample_rate, params)
        rate = float(self.params.get("rate_hz", 2.5))
        wf = LFOType(self.params.get("waveform", "sine"))
        depth = float(self.params.get("depth", 1.0))
        bipolar = bool(self.params.get("bipolar", True))
        self.lfo = LFO(sample_rate, rate, wf, depth, bipolar)

    def set_sample_rate(self, sr: int) -> None:
        super().set_sample_rate(sr)
        self.lfo.set_sample_rate(sr)

    def reset_state(self) -> None:
        self.lfo.reset_phase()

    def process(self, block_size: int, inputs: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        self.lfo.set_rate(float(self.params.get("rate_hz", 2.5)))
        self.lfo.lfo_type = LFOType(self.params.get("waveform", "sine"))
        self.lfo.depth = float(self.params.get("depth", 1.0))
        self.lfo.bipolar = bool(self.params.get("bipolar", True))

        sync = inputs.get("sync")
        out = self.lfo.process_block(block_size, sync_triggers=sync)
        return {"out": out}


class MixerNode(BaseNode):
    """4-channel summing audio mixer."""

    TYPE_ID = "mixer"
    DISPLAY_NAME = "4-Channel Mixer"
    CATEGORY = "Utility"
    DESCRIPTION = "Summing mixer for combining multiple audio or control channels."

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {
            "ch1_gain": 0.8,
            "ch2_gain": 0.8,
            "ch3_gain": 0.8,
            "ch4_gain": 0.8,
            "master_gain": 1.0,
        }

    @classmethod
    def get_metadata(cls) -> NodeMetadata:
        return NodeMetadata(
            type_id=cls.TYPE_ID,
            display_name=cls.DISPLAY_NAME,
            category=cls.CATEGORY,
            description=cls.DESCRIPTION,
            inputs=[
                PinSchema(name="in1", pin_type=PinType.AUDIO, direction=PinDirection.INPUT, default_value=0.0),
                PinSchema(name="in2", pin_type=PinType.AUDIO, direction=PinDirection.INPUT, default_value=0.0),
                PinSchema(name="in3", pin_type=PinType.AUDIO, direction=PinDirection.INPUT, default_value=0.0),
                PinSchema(name="in4", pin_type=PinType.AUDIO, direction=PinDirection.INPUT, default_value=0.0),
            ],
            outputs=[
                PinSchema(name="out", pin_type=PinType.AUDIO, direction=PinDirection.OUTPUT, default_value=0.0),
            ],
            default_params=cls.get_default_params(),
        )

    def process(self, block_size: int, inputs: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        out = np.zeros(block_size, dtype=np.float32)
        for i in range(1, 5):
            pin_name = f"in{i}"
            gain_name = f"ch{i}_gain"
            if pin_name in inputs:
                gain = float(self.params.get(gain_name, 0.8))
                out += inputs[pin_name] * gain

        master_gain = float(self.params.get("master_gain", 1.0))
        out *= master_gain
        return {"out": out}


class DelayNode(BaseNode):
    """Stereo Ping-Pong / Tape delay effect node."""

    TYPE_ID = "delay"
    DISPLAY_NAME = "Stereo Delay"
    CATEGORY = "Effects"
    DESCRIPTION = "Fractional stereo delay with ping-pong crossfeed and high frequency damping."

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {
            "time_sec": 0.3,
            "feedback": 0.45,
            "damping": 0.25,
            "mix": 0.35,
            "ping_pong": True,
        }

    @classmethod
    def get_metadata(cls) -> NodeMetadata:
        return NodeMetadata(
            type_id=cls.TYPE_ID,
            display_name=cls.DISPLAY_NAME,
            category=cls.CATEGORY,
            description=cls.DESCRIPTION,
            inputs=[
                PinSchema(name="in_l", pin_type=PinType.AUDIO, direction=PinDirection.INPUT, default_value=0.0),
                PinSchema(name="in_r", pin_type=PinType.AUDIO, direction=PinDirection.INPUT, default_value=0.0),
            ],
            outputs=[
                PinSchema(name="out_l", pin_type=PinType.AUDIO, direction=PinDirection.OUTPUT, default_value=0.0),
                PinSchema(name="out_r", pin_type=PinType.AUDIO, direction=PinDirection.OUTPUT, default_value=0.0),
            ],
            default_params=cls.get_default_params(),
        )

    def __init__(self, node_id: str, sample_rate: int = 44100, params: Optional[Dict[str, Any]] = None):
        super().__init__(node_id, sample_rate, params)
        t = float(self.params.get("time_sec", 0.3))
        fb = float(self.params.get("feedback", 0.45))
        damp = float(self.params.get("damping", 0.25))
        mix = float(self.params.get("mix", 0.35))
        pp = bool(self.params.get("ping_pong", True))
        self.delay = DelayEffect(sample_rate, t, fb, damp, mix, pp)

    def set_sample_rate(self, sr: int) -> None:
        super().set_sample_rate(sr)
        self.delay.set_sample_rate(sr)

    def process(self, block_size: int, inputs: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        self.delay.delay_time_sec = float(self.params.get("time_sec", 0.3))
        self.delay.feedback = float(self.params.get("feedback", 0.45))
        self.delay.damping = float(self.params.get("damping", 0.25))
        self.delay.mix = float(self.params.get("mix", 0.35))
        self.delay.ping_pong = bool(self.params.get("ping_pong", True))

        in_l = inputs.get("in_l", np.zeros(block_size, dtype=np.float32))
        in_r = inputs.get("in_r", in_l)  # Fallback to mono if in_r not connected

        out_l = np.zeros(block_size, dtype=np.float32)
        out_r = np.zeros(block_size, dtype=np.float32)

        for i in range(block_size):
            ol, or_val = self.delay.process_sample(float(in_l[i]), float(in_r[i]))
            out_l[i] = ol
            out_r[i] = or_val

        return {"out_l": out_l, "out_r": out_r}


class DistortionNode(BaseNode):
    """Non-linear saturation and distortion node."""

    TYPE_ID = "distortion"
    DISPLAY_NAME = "Waveshaper / Drive"
    CATEGORY = "Effects"
    DESCRIPTION = "Harmonic saturation: Tanh tape drive, Cubic soft clip, Diode, and Wavefolder."

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {
            "type": "tanh",
            "drive": 2.5,
            "mix": 1.0,
        }

    @classmethod
    def get_metadata(cls) -> NodeMetadata:
        return NodeMetadata(
            type_id=cls.TYPE_ID,
            display_name=cls.DISPLAY_NAME,
            category=cls.CATEGORY,
            description=cls.DESCRIPTION,
            inputs=[
                PinSchema(name="in", pin_type=PinType.AUDIO, direction=PinDirection.INPUT, default_value=0.0),
            ],
            outputs=[
                PinSchema(name="out", pin_type=PinType.AUDIO, direction=PinDirection.OUTPUT, default_value=0.0),
            ],
            default_params=cls.get_default_params(),
        )

    def __init__(self, node_id: str, sample_rate: int = 44100, params: Optional[Dict[str, Any]] = None):
        super().__init__(node_id, sample_rate, params)
        dtype = DistortionType(self.params.get("type", "tanh"))
        drive = float(self.params.get("drive", 2.5))
        mix = float(self.params.get("mix", 1.0))
        self.shaper = Waveshaper(dtype, drive, mix)

    def process(self, block_size: int, inputs: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        self.shaper.distortion_type = DistortionType(self.params.get("type", "tanh"))
        self.shaper.drive = float(self.params.get("drive", 2.5))
        self.shaper.mix = float(self.params.get("mix", 1.0))

        in_buf = inputs.get("in", np.zeros(block_size, dtype=np.float32))
        out = np.zeros(block_size, dtype=np.float32)

        for i in range(block_size):
            out[i] = self.shaper.process_sample(float(in_buf[i]))

        return {"out": out}


class ReverbNode(BaseNode):
    """Schroeder-Moorer digital reverb node."""

    TYPE_ID = "reverb"
    DISPLAY_NAME = "Schroeder Reverb"
    CATEGORY = "Effects"
    DESCRIPTION = "8-comb 4-allpass reverberator for dense algorithmic acoustic spaces."

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {
            "room_size": 0.6,
            "damping": 0.4,
            "wet": 0.35,
            "dry": 0.75,
            "width": 1.0,
        }

    @classmethod
    def get_metadata(cls) -> NodeMetadata:
        return NodeMetadata(
            type_id=cls.TYPE_ID,
            display_name=cls.DISPLAY_NAME,
            category=cls.CATEGORY,
            description=cls.DESCRIPTION,
            inputs=[
                PinSchema(name="in_l", pin_type=PinType.AUDIO, direction=PinDirection.INPUT, default_value=0.0),
                PinSchema(name="in_r", pin_type=PinType.AUDIO, direction=PinDirection.INPUT, default_value=0.0),
            ],
            outputs=[
                PinSchema(name="out_l", pin_type=PinType.AUDIO, direction=PinDirection.OUTPUT, default_value=0.0),
                PinSchema(name="out_r", pin_type=PinType.AUDIO, direction=PinDirection.OUTPUT, default_value=0.0),
            ],
            default_params=cls.get_default_params(),
        )

    def __init__(self, node_id: str, sample_rate: int = 44100, params: Optional[Dict[str, Any]] = None):
        super().__init__(node_id, sample_rate, params)
        rs = float(self.params.get("room_size", 0.6))
        damp = float(self.params.get("damping", 0.4))
        wet = float(self.params.get("wet", 0.35))
        dry = float(self.params.get("dry", 0.75))
        w = float(self.params.get("width", 1.0))
        self.reverb = SchroederReverb(sample_rate, rs, damp, wet, dry, w)

    def set_sample_rate(self, sr: int) -> None:
        super().set_sample_rate(sr)
        self.reverb.set_sample_rate(sr)

    def process(self, block_size: int, inputs: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        self.reverb.room_size = float(self.params.get("room_size", 0.6))
        self.reverb.damping = float(self.params.get("damping", 0.4))
        self.reverb.wet = float(self.params.get("wet", 0.35))
        self.reverb.dry = float(self.params.get("dry", 0.75))
        self.reverb.width = float(self.params.get("width", 1.0))

        in_l = inputs.get("in_l", np.zeros(block_size, dtype=np.float32))
        in_r = inputs.get("in_r", in_l)

        out_l = np.zeros(block_size, dtype=np.float32)
        out_r = np.zeros(block_size, dtype=np.float32)

        for i in range(block_size):
            ol, or_val = self.reverb.process_sample(float(in_l[i]), float(in_r[i]))
            out_l[i] = ol
            out_r[i] = or_val

        return {"out_l": out_l, "out_r": out_r}


class PannerNode(BaseNode):
    """Constant-power stereo panner node."""

    TYPE_ID = "panner"
    DISPLAY_NAME = "Stereo Panner"
    CATEGORY = "Utility"
    DESCRIPTION = "Equal-power stereo positioning with CV pan modulation."

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {"pan": 0.0}

    @classmethod
    def get_metadata(cls) -> NodeMetadata:
        return NodeMetadata(
            type_id=cls.TYPE_ID,
            display_name=cls.DISPLAY_NAME,
            category=cls.CATEGORY,
            description=cls.DESCRIPTION,
            inputs=[
                PinSchema(name="in", pin_type=PinType.AUDIO, direction=PinDirection.INPUT, default_value=0.0),
                PinSchema(name="pan_mod", pin_type=PinType.CONTROL, direction=PinDirection.INPUT, default_value=0.0),
            ],
            outputs=[
                PinSchema(name="out_l", pin_type=PinType.AUDIO, direction=PinDirection.OUTPUT, default_value=0.0),
                PinSchema(name="out_r", pin_type=PinType.AUDIO, direction=PinDirection.OUTPUT, default_value=0.0),
            ],
            default_params=cls.get_default_params(),
        )

    def __init__(self, node_id: str, sample_rate: int = 44100, params: Optional[Dict[str, Any]] = None):
        super().__init__(node_id, sample_rate, params)
        p = float(self.params.get("pan", 0.0))
        self.panner = StereoPanner(p)

    def process(self, block_size: int, inputs: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        self.panner.pan = float(self.params.get("pan", 0.0))
        in_buf = inputs.get("in", np.zeros(block_size, dtype=np.float32))
        pan_mod = inputs.get("pan_mod")

        out_l = np.zeros(block_size, dtype=np.float32)
        out_r = np.zeros(block_size, dtype=np.float32)

        for i in range(block_size):
            pm = float(pan_mod[i]) if pan_mod is not None else 0.0
            x = float(in_buf[i])
            ol, or_val = self.panner.process_sample(x, x, pan_mod=pm)
            out_l[i] = ol
            out_r[i] = or_val

        return {"out_l": out_l, "out_r": out_r}


class OutputNode(BaseNode):
    """Master audio output sink for Left and Right stereo channels."""

    TYPE_ID = "audio_output"
    DISPLAY_NAME = "Master Audio Out"
    CATEGORY = "Master"
    DESCRIPTION = "Terminal audio destination with lookahead soft limiting and master volume."

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {
            "master_volume": 0.85,
            "limiter_enabled": True,
        }

    @classmethod
    def get_metadata(cls) -> NodeMetadata:
        return NodeMetadata(
            type_id=cls.TYPE_ID,
            display_name=cls.DISPLAY_NAME,
            category=cls.CATEGORY,
            description=cls.DESCRIPTION,
            inputs=[
                PinSchema(name="left", pin_type=PinType.AUDIO, direction=PinDirection.INPUT, default_value=0.0),
                PinSchema(name="right", pin_type=PinType.AUDIO, direction=PinDirection.INPUT, default_value=0.0),
            ],
            outputs=[],
            default_params=cls.get_default_params(),
        )

    def process(self, block_size: int, inputs: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        vol = float(self.params.get("master_volume", 0.85))
        limit = bool(self.params.get("limiter_enabled", True))

        left = inputs.get("left", np.zeros(block_size, dtype=np.float32)) * vol
        right = inputs.get("right", left) * vol

        if limit:
            # Soft tanh master limiter to prevent digital overs
            left = np.tanh(left)
            right = np.tanh(right)

        return {"left": left, "right": right}


class SequencerNode(BaseNode):
    """16-step modular pattern sequencer with pitch, gate, slide, and accent."""

    TYPE_ID = "sequencer"
    DISPLAY_NAME = "16-Step Sequencer"
    CATEGORY = "Modulation"
    DESCRIPTION = "16-step pattern sequencer with 303-style portamento slide and accent dynamics."

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {
            "bpm": 125.0,
            "gate_length": 0.65,
            "slide_time": 0.06,
        }

    @classmethod
    def get_metadata(cls) -> NodeMetadata:
        return NodeMetadata(
            type_id=cls.TYPE_ID,
            display_name=cls.DISPLAY_NAME,
            category=cls.CATEGORY,
            description=cls.DESCRIPTION,
            inputs=[
                PinSchema(name="clock", pin_type=PinType.CONTROL, direction=PinDirection.INPUT, default_value=0.0),
                PinSchema(name="reset", pin_type=PinType.CONTROL, direction=PinDirection.INPUT, default_value=0.0),
            ],
            outputs=[
                PinSchema(name="pitch", pin_type=PinType.CONTROL, direction=PinDirection.OUTPUT, default_value=440.0, unit="Hz"),
                PinSchema(name="gate", pin_type=PinType.CONTROL, direction=PinDirection.OUTPUT, default_value=0.0),
                PinSchema(name="accent", pin_type=PinType.CONTROL, direction=PinDirection.OUTPUT, default_value=0.0),
            ],
            default_params=cls.get_default_params(),
        )

    def __init__(self, node_id: str, sample_rate: int = 44100, params: Optional[Dict[str, Any]] = None):
        super().__init__(node_id, sample_rate, params)
        bpm = float(self.params.get("bpm", 125.0))
        gl = float(self.params.get("gate_length", 0.65))
        st = float(self.params.get("slide_time", 0.06))
        self.seq = StepSequencer(sample_rate, bpm=bpm, gate_length=gl, slide_time=st)

    def set_sample_rate(self, sr: int) -> None:
        super().set_sample_rate(sr)
        self.seq.set_sample_rate(sr)

    def reset_state(self) -> None:
        self.seq.reset()

    def process(self, block_size: int, inputs: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        self.seq.set_bpm(float(self.params.get("bpm", 125.0)))
        self.seq.gate_length = float(self.params.get("gate_length", 0.65))
        self.seq.slide_time = float(self.params.get("slide_time", 0.06))

        pitches = np.zeros(block_size, dtype=np.float32)
        gates = np.zeros(block_size, dtype=np.float32)
        accents = np.zeros(block_size, dtype=np.float32)

        for i in range(block_size):
            p, g, a = self.seq.process_sample()
            pitches[i] = p
            gates[i] = g
            accents[i] = a

        return {"pitch": pitches, "gate": gates, "accent": accents}


class KarplusStrongNode(BaseNode):
    """Karplus-Strong physical modeling plucked string synthesizer."""

    TYPE_ID = "karplus_strong"
    DISPLAY_NAME = "Karplus String Pluck"
    CATEGORY = "Generators"
    DESCRIPTION = "Physical modeling string synthesis for plucked acoustic instruments, harp, and guitars."

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {
            "frequency": 220.0,
            "decay": 0.985,
            "damping": 0.35,
        }

    @classmethod
    def get_metadata(cls) -> NodeMetadata:
        return NodeMetadata(
            type_id=cls.TYPE_ID,
            display_name=cls.DISPLAY_NAME,
            category=cls.CATEGORY,
            description=cls.DESCRIPTION,
            inputs=[
                PinSchema(name="trigger", pin_type=PinType.CONTROL, direction=PinDirection.INPUT, default_value=0.0),
                PinSchema(name="freq_mod", pin_type=PinType.CONTROL, direction=PinDirection.INPUT, default_value=0.0, unit="Hz"),
            ],
            outputs=[
                PinSchema(name="out", pin_type=PinType.AUDIO, direction=PinDirection.OUTPUT, default_value=0.0),
            ],
            default_params=cls.get_default_params(),
        )

    def __init__(self, node_id: str, sample_rate: int = 44100, params: Optional[Dict[str, Any]] = None):
        super().__init__(node_id, sample_rate, params)
        freq = float(self.params.get("frequency", 220.0))
        dec = float(self.params.get("decay", 0.985))
        damp = float(self.params.get("damping", 0.35))
        self.string = KarplusStrongString(sample_rate, freq, dec, damp)

    def set_sample_rate(self, sr: int) -> None:
        super().set_sample_rate(sr)
        self.string.set_sample_rate(sr)

    def reset_state(self) -> None:
        self.string.trigger_pluck()

    def process(self, block_size: int, inputs: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        self.string.set_frequency(float(self.params.get("frequency", 220.0)))
        self.string.decay = float(self.params.get("decay", 0.985))
        self.string.damping = float(self.params.get("damping", 0.35))

        trig = inputs.get("trigger")
        fm = inputs.get("freq_mod")
        out = self.string.process_block(block_size, freq_mod=fm, trigger_triggers=trig)
        return {"out": out}


class FormantNode(BaseNode):
    """Triple-peak bandpass vowel formant filter."""

    TYPE_ID = "formant_filter"
    DISPLAY_NAME = "Vowel Formant Filter"
    CATEGORY = "Filters"
    DESCRIPTION = "Human vocal tract vowel resonator with smooth morphing across A, E, I, O, U phonemes."

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {
            "vowel_pos": 0.0,
            "resonance_scale": 1.2,
        }

    @classmethod
    def get_metadata(cls) -> NodeMetadata:
        return NodeMetadata(
            type_id=cls.TYPE_ID,
            display_name=cls.DISPLAY_NAME,
            category=cls.CATEGORY,
            description=cls.DESCRIPTION,
            inputs=[
                PinSchema(name="in", pin_type=PinType.AUDIO, direction=PinDirection.INPUT, default_value=0.0),
                PinSchema(name="vowel_mod", pin_type=PinType.CONTROL, direction=PinDirection.INPUT, default_value=0.0),
            ],
            outputs=[
                PinSchema(name="out", pin_type=PinType.AUDIO, direction=PinDirection.OUTPUT, default_value=0.0),
            ],
            default_params=cls.get_default_params(),
        )

    def __init__(self, node_id: str, sample_rate: int = 44100, params: Optional[Dict[str, Any]] = None):
        super().__init__(node_id, sample_rate, params)
        v = float(self.params.get("vowel_pos", 0.0))
        r = float(self.params.get("resonance_scale", 1.2))
        self.filter = FormantFilter(sample_rate, v, r)

    def set_sample_rate(self, sr: int) -> None:
        super().set_sample_rate(sr)
        self.filter.set_sample_rate(sr)

    def reset_state(self) -> None:
        self.filter.reset_state()

    def process(self, block_size: int, inputs: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        self.filter.set_vowel(float(self.params.get("vowel_pos", 0.0)))
        self.filter.resonance_scale = float(self.params.get("resonance_scale", 1.2))

        in_buf = inputs.get("in", np.zeros(block_size, dtype=np.float32))
        vmod = inputs.get("vowel_mod")
        out = self.filter.process_block(in_buf, vowel_mod=vmod)
        return {"out": out}


class ChorusNode(BaseNode):
    """Stereo BBD Chorus and Flanger effect with quadrature modulation."""

    TYPE_ID = "chorus"
    DISPLAY_NAME = "Stereo Chorus / Flanger"
    CATEGORY = "Effects"
    DESCRIPTION = "BBD analog-modeled stereo chorus and flanger with dual 90-degree quadrature LFOs."

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {
            "rate_hz": 1.2,
            "depth_ms": 3.5,
            "base_delay_ms": 15.0,
            "feedback": 0.25,
            "mix": 0.5,
            "flanger_mode": False,
        }

    @classmethod
    def get_metadata(cls) -> NodeMetadata:
        return NodeMetadata(
            type_id=cls.TYPE_ID,
            display_name=cls.DISPLAY_NAME,
            category=cls.CATEGORY,
            description=cls.DESCRIPTION,
            inputs=[
                PinSchema(name="in_l", pin_type=PinType.AUDIO, direction=PinDirection.INPUT, default_value=0.0),
                PinSchema(name="in_r", pin_type=PinType.AUDIO, direction=PinDirection.INPUT, default_value=0.0),
            ],
            outputs=[
                PinSchema(name="out_l", pin_type=PinType.AUDIO, direction=PinDirection.OUTPUT, default_value=0.0),
                PinSchema(name="out_r", pin_type=PinType.AUDIO, direction=PinDirection.OUTPUT, default_value=0.0),
            ],
            default_params=cls.get_default_params(),
        )

    def __init__(self, node_id: str, sample_rate: int = 44100, params: Optional[Dict[str, Any]] = None):
        super().__init__(node_id, sample_rate, params)
        rate = float(self.params.get("rate_hz", 1.2))
        depth = float(self.params.get("depth_ms", 3.5))
        delay = float(self.params.get("base_delay_ms", 15.0))
        fb = float(self.params.get("feedback", 0.25))
        mix = float(self.params.get("mix", 0.5))
        flange = bool(self.params.get("flanger_mode", False))
        self.chorus = StereoChorusEffect(sample_rate, rate, depth, delay, fb, mix, flange)

    def set_sample_rate(self, sr: int) -> None:
        super().set_sample_rate(sr)
        self.chorus.set_sample_rate(sr)

    def reset_state(self) -> None:
        self.chorus.reset_state()

    def process(self, block_size: int, inputs: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        self.chorus.rate_hz = float(self.params.get("rate_hz", 1.2))
        self.chorus.depth_ms = float(self.params.get("depth_ms", 3.5))
        self.chorus.base_delay_ms = float(self.params.get("base_delay_ms", 15.0))
        self.chorus.feedback = float(self.params.get("feedback", 0.25))
        self.chorus.mix = float(self.params.get("mix", 0.5))
        self.chorus.flanger_mode = bool(self.params.get("flanger_mode", False))

        in_l = inputs.get("in_l", np.zeros(block_size, dtype=np.float32))
        in_r = inputs.get("in_r", in_l)

        out_l = np.zeros(block_size, dtype=np.float32)
        out_r = np.zeros(block_size, dtype=np.float32)

        for i in range(block_size):
            ol, or_val = self.chorus.process_sample(float(in_l[i]), float(in_r[i]))
            out_l[i] = ol
            out_r[i] = or_val

        return {"out_l": out_l, "out_r": out_r}


class KickNode(BaseNode):
    """Roland TR-808 style analog kick drum synthesizer."""

    TYPE_ID = "drum_kick"
    DISPLAY_NAME = "TR-808 Kick Drum"
    CATEGORY = "Percussion"
    DESCRIPTION = "Analog kick drum generator with fast exponential pitch dive, attack click, and saturation."

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {
            "pitch_start": 220.0,
            "pitch_end": 48.0,
            "pitch_decay": 0.04,
            "decay_time": 0.6,
            "click_amount": 0.35,
            "drive": 1.4,
        }

    @classmethod
    def get_metadata(cls) -> NodeMetadata:
        return NodeMetadata(
            type_id=cls.TYPE_ID,
            display_name=cls.DISPLAY_NAME,
            category=cls.CATEGORY,
            description=cls.DESCRIPTION,
            inputs=[
                PinSchema(name="trigger", pin_type=PinType.CONTROL, direction=PinDirection.INPUT, default_value=0.0),
            ],
            outputs=[
                PinSchema(name="out", pin_type=PinType.AUDIO, direction=PinDirection.OUTPUT, default_value=0.0),
            ],
            default_params=cls.get_default_params(),
        )

    def __init__(self, node_id: str, sample_rate: int = 44100, params: Optional[Dict[str, Any]] = None):
        super().__init__(node_id, sample_rate, params)
        p_start = float(self.params.get("pitch_start", 220.0))
        p_end = float(self.params.get("pitch_end", 48.0))
        p_dec = float(self.params.get("pitch_decay", 0.04))
        dec = float(self.params.get("decay_time", 0.6))
        click = float(self.params.get("click_amount", 0.35))
        drv = float(self.params.get("drive", 1.4))
        self.kick = Kick808(sample_rate, p_start, p_end, p_dec, dec, click, drv)

    def process(self, block_size: int, inputs: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        self.kick.pitch_start = float(self.params.get("pitch_start", 220.0))
        self.kick.pitch_end = float(self.params.get("pitch_end", 48.0))
        self.kick.pitch_decay = float(self.params.get("pitch_decay", 0.04))
        self.kick.decay_time = float(self.params.get("decay_time", 0.6))
        self.kick.click_amount = float(self.params.get("click_amount", 0.35))
        self.kick.drive = float(self.params.get("drive", 1.4))

        trig = inputs.get("trigger")
        out = np.zeros(block_size, dtype=np.float32)

        for i in range(block_size):
            if trig is not None and trig[i] > 0.5:
                self.kick.trigger(velocity=float(trig[i]))
            out[i] = self.kick.process_sample()

        return {"out": out}


class SnareNode(BaseNode):
    """Roland TR-808 style analog snare drum synthesizer."""

    TYPE_ID = "drum_snare"
    DISPLAY_NAME = "TR-808 Snare Drum"
    CATEGORY = "Percussion"
    DESCRIPTION = "Analog snare drum combining dual harmonic body tones and bandpass snappy noise."

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {
            "tone_freq": 180.0,
            "tone_decay": 0.15,
            "snappy_decay": 0.25,
            "snappy_mix": 0.65,
        }

    @classmethod
    def get_metadata(cls) -> NodeMetadata:
        return NodeMetadata(
            type_id=cls.TYPE_ID,
            display_name=cls.DISPLAY_NAME,
            category=cls.CATEGORY,
            description=cls.DESCRIPTION,
            inputs=[
                PinSchema(name="trigger", pin_type=PinType.CONTROL, direction=PinDirection.INPUT, default_value=0.0),
            ],
            outputs=[
                PinSchema(name="out", pin_type=PinType.AUDIO, direction=PinDirection.OUTPUT, default_value=0.0),
            ],
            default_params=cls.get_default_params(),
        )

    def __init__(self, node_id: str, sample_rate: int = 44100, params: Optional[Dict[str, Any]] = None):
        super().__init__(node_id, sample_rate, params)
        tf = float(self.params.get("tone_freq", 180.0))
        td = float(self.params.get("tone_decay", 0.15))
        sd = float(self.params.get("snappy_decay", 0.25))
        sm = float(self.params.get("snappy_mix", 0.65))
        self.snare = Snare808(sample_rate, tf, td, sd, sm)

    def process(self, block_size: int, inputs: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        self.snare.tone_freq = float(self.params.get("tone_freq", 180.0))
        self.snare.tone_decay = float(self.params.get("tone_decay", 0.15))
        self.snare.snappy_decay = float(self.params.get("snappy_decay", 0.25))
        self.snare.snappy_mix = float(self.params.get("snappy_mix", 0.65))

        trig = inputs.get("trigger")
        out = np.zeros(block_size, dtype=np.float32)

        for i in range(block_size):
            if trig is not None and trig[i] > 0.5:
                self.snare.trigger(velocity=float(trig[i]))
            out[i] = self.snare.process_sample()

        return {"out": out}


class HiHatNode(BaseNode):
    """Roland TR-808 style 6-oscillator inharmonic metallic Hi-Hat."""

    TYPE_ID = "drum_hihat"
    DISPLAY_NAME = "TR-808 6-Osc Hi-Hat"
    CATEGORY = "Percussion"
    DESCRIPTION = "6-oscillator inharmonic square wave cluster through resonant highpass for metallic cymbals."

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {
            "decay_time": 0.06,
            "cutoff_hz": 7200.0,
            "open_hat": False,
        }

    @classmethod
    def get_metadata(cls) -> NodeMetadata:
        return NodeMetadata(
            type_id=cls.TYPE_ID,
            display_name=cls.DISPLAY_NAME,
            category=cls.CATEGORY,
            description=cls.DESCRIPTION,
            inputs=[
                PinSchema(name="trigger", pin_type=PinType.CONTROL, direction=PinDirection.INPUT, default_value=0.0),
            ],
            outputs=[
                PinSchema(name="out", pin_type=PinType.AUDIO, direction=PinDirection.OUTPUT, default_value=0.0),
            ],
            default_params=cls.get_default_params(),
        )

    def __init__(self, node_id: str, sample_rate: int = 44100, params: Optional[Dict[str, Any]] = None):
        super().__init__(node_id, sample_rate, params)
        d = float(self.params.get("decay_time", 0.06))
        c = float(self.params.get("cutoff_hz", 7200.0))
        self.hihat = HiHat808(sample_rate, d, c)

    def process(self, block_size: int, inputs: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        self.hihat.decay_time = float(self.params.get("decay_time", 0.06))
        self.hihat.cutoff_hz = float(self.params.get("cutoff_hz", 7200.0))
        is_open = bool(self.params.get("open_hat", False))

        trig = inputs.get("trigger")
        out = np.zeros(block_size, dtype=np.float32)

        for i in range(block_size):
            if trig is not None and trig[i] > 0.5:
                self.hihat.trigger(velocity=float(trig[i]), open_hat=is_open)
            out[i] = self.hihat.process_sample()

        return {"out": out}


class RingModNode(BaseNode):
    """Audio-rate balanced four-quadrant multiplier (Ring Modulator)."""

    TYPE_ID = "ring_mod"
    DISPLAY_NAME = "Ring Modulator"
    CATEGORY = "Modulation"
    DESCRIPTION = "Four-quadrant audio-rate balanced multiplier generating sum and difference sidebands."

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {
            "internal_carrier_freq": 440.0,
            "use_internal_carrier": False,
            "mix": 1.0,
        }

    @classmethod
    def get_metadata(cls) -> NodeMetadata:
        return NodeMetadata(
            type_id=cls.TYPE_ID,
            display_name=cls.DISPLAY_NAME,
            category=cls.CATEGORY,
            description=cls.DESCRIPTION,
            inputs=[
                PinSchema(name="carrier", pin_type=PinType.AUDIO, direction=PinDirection.INPUT, default_value=0.0),
                PinSchema(name="modulator", pin_type=PinType.AUDIO, direction=PinDirection.INPUT, default_value=0.0),
            ],
            outputs=[
                PinSchema(name="out", pin_type=PinType.AUDIO, direction=PinDirection.OUTPUT, default_value=0.0),
            ],
            default_params=cls.get_default_params(),
        )

    def __init__(self, node_id: str, sample_rate: int = 44100, params: Optional[Dict[str, Any]] = None):
        super().__init__(node_id, sample_rate, params)
        self._phase = 0.0

    def process(self, block_size: int, inputs: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        mix = float(self.params.get("mix", 1.0))
        use_int = bool(self.params.get("use_internal_carrier", False))
        int_freq = float(self.params.get("internal_carrier_freq", 440.0))

        mod_sig = inputs.get("modulator", np.zeros(block_size, dtype=np.float32))

        if use_int:
            # Generate internal sine carrier
            carrier = np.zeros(block_size, dtype=np.float32)
            dt = int_freq / self.sample_rate
            for i in range(block_size):
                carrier[i] = math.sin(2.0 * math.pi * self._phase)
                self._phase = (self._phase + dt) % 1.0
        else:
            carrier = inputs.get("carrier", np.zeros(block_size, dtype=np.float32))

        ring_out = carrier * mod_sig
        out = (1.0 - mix) * mod_sig + mix * ring_out
        return {"out": out}


NODE_REGISTRY: Dict[str, type[BaseNode]] = {
    OscillatorNode.TYPE_ID: OscillatorNode,
    FilterNode.TYPE_ID: FilterNode,
    ADSRNode.TYPE_ID: ADSRNode,
    VCANode.TYPE_ID: VCANode,
    LFONode.TYPE_ID: LFONode,
    MixerNode.TYPE_ID: MixerNode,
    DelayNode.TYPE_ID: DelayNode,
    DistortionNode.TYPE_ID: DistortionNode,
    ReverbNode.TYPE_ID: ReverbNode,
    PannerNode.TYPE_ID: PannerNode,
    OutputNode.TYPE_ID: OutputNode,
    # New Advanced DSP Nodes
    SequencerNode.TYPE_ID: SequencerNode,
    KarplusStrongNode.TYPE_ID: KarplusStrongNode,
    FormantNode.TYPE_ID: FormantNode,
    ChorusNode.TYPE_ID: ChorusNode,
    KickNode.TYPE_ID: KickNode,
    SnareNode.TYPE_ID: SnareNode,
    HiHatNode.TYPE_ID: HiHatNode,
    RingModNode.TYPE_ID: RingModNode,
}

