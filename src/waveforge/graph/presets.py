"""Built-in production synthesizer patches and modular presets."""

from __future__ import annotations
from typing import Dict, Callable
from waveforge.graph.patch import NodeGraph


def create_acid_303_patch() -> NodeGraph:
    """Roland TB-303 style acid bass patch with resonant filter sweep and diode/tanh drive."""
    g = NodeGraph(name="Acid 303 Bass", sample_rate=44100, block_size=128)

    # 1. Oscillator (Sawtooth)
    g.add_node("oscillator", "osc1", x=60, y=100, params={"waveform": "saw", "frequency": 110.0})

    # 2. Filter envelope
    g.add_node("adsr", "env_filter", x=60, y=320, params={"attack": 0.005, "decay": 0.22, "sustain": 0.15, "release": 0.12})

    # 3. Resonant Lowpass Filter
    g.add_node("biquad_filter", "flt1", x=300, y=100, params={"filter_type": "lowpass", "cutoff_hz": 400.0, "q": 4.5})

    # 4. Amp envelope
    g.add_node("adsr", "env_amp", x=300, y=320, params={"attack": 0.005, "decay": 0.28, "sustain": 0.2, "release": 0.15})

    # 5. VCA
    g.add_node("vca", "vca1", x=520, y=100, params={"gain": 1.2})

    # 6. Distortion / Overdrive
    g.add_node("distortion", "dist1", x=720, y=100, params={"type": "tanh", "drive": 3.2, "mix": 0.85})

    # 7. Delay
    g.add_node("delay", "dly1", x=920, y=100, params={"time_sec": 0.25, "feedback": 0.35, "mix": 0.25, "ping_pong": True})

    # 8. Master Output
    g.add_node("audio_output", "out1", x=1140, y=100, params={"master_volume": 0.8, "limiter_enabled": True})

    # Connections
    g.connect("osc1", "out", "flt1", "in")
    g.connect("flt1", "out", "vca1", "in")
    g.connect("env_amp", "out", "vca1", "cv")
    g.connect("vca1", "out", "dist1", "in")
    g.connect("dist1", "out", "dly1", "in_l")
    g.connect("dist1", "out", "dly1", "in_r")
    g.connect("dly1", "out_l", "out1", "left")
    g.connect("dly1", "out_r", "out1", "right")

    return g


def create_sub_bass_patch() -> NodeGraph:
    """Deep solid sub bass combining sine foundation with harmonic square pulse."""
    g = NodeGraph(name="Sub Bass Foundation", sample_rate=44100, block_size=128)

    # Sine sub oscillator
    g.add_node("oscillator", "sub_osc", x=60, y=80, params={"waveform": "sine", "frequency": 55.0})
    # Harmonic square oscillator
    g.add_node("oscillator", "mid_osc", x=60, y=280, params={"waveform": "square", "frequency": 110.0, "pulse_width": 0.45})

    # Mixer
    g.add_node("mixer", "mix1", x=300, y=160, params={"ch1_gain": 0.9, "ch2_gain": 0.35, "master_gain": 1.0})

    # Filter
    g.add_node("biquad_filter", "flt1", x=520, y=160, params={"filter_type": "lowpass", "cutoff_hz": 280.0, "q": 1.2})

    # Envelope
    g.add_node("adsr", "env1", x=520, y=360, params={"attack": 0.008, "decay": 0.35, "sustain": 0.7, "release": 0.2})

    # VCA
    g.add_node("vca", "vca1", x=720, y=160, params={"gain": 1.0})

    # Distortion saturation
    g.add_node("distortion", "sat1", x=920, y=160, params={"type": "cubic", "drive": 1.5, "mix": 0.4})

    # Audio Output
    g.add_node("audio_output", "out1", x=1120, y=160, params={"master_volume": 0.9, "limiter_enabled": True})

    g.connect("sub_osc", "out", "mix1", "in1")
    g.connect("mid_osc", "out", "mix1", "in2")
    g.connect("mix1", "out", "flt1", "in")
    g.connect("flt1", "out", "vca1", "in")
    g.connect("env1", "out", "vca1", "cv")
    g.connect("vca1", "out", "sat1", "in")
    g.connect("sat1", "out", "out1", "left")
    g.connect("sat1", "out", "out1", "right")

    return g


def create_lush_pad_patch() -> NodeGraph:
    """Atmospheric ambient pad with LFO filter sweep and Schroeder reverb."""
    g = NodeGraph(name="Lush Ambient Pad", sample_rate=44100, block_size=128)

    # Detuned dual saws
    g.add_node("oscillator", "osc1", x=60, y=80, params={"waveform": "saw", "frequency": 220.0})
    g.add_node("oscillator", "osc2", x=60, y=260, params={"waveform": "saw", "frequency": 221.8})

    # Mixer
    g.add_node("mixer", "mix1", x=280, y=160, params={"ch1_gain": 0.6, "ch2_gain": 0.6, "master_gain": 0.9})

    # Filter
    g.add_node("biquad_filter", "flt1", x=480, y=160, params={"filter_type": "lowpass", "cutoff_hz": 900.0, "q": 1.8})

    # LFO for slow sweep
    g.add_node("lfo", "lfo1", x=480, y=360, params={"rate_hz": 0.35, "waveform": "triangle", "depth": 1.0})

    # Envelope (long attack and release)
    g.add_node("adsr", "env1", x=700, y=360, params={"attack": 0.8, "decay": 1.2, "sustain": 0.8, "release": 1.5})

    # VCA
    g.add_node("vca", "vca1", x=700, y=160, params={"gain": 0.9})

    # Stereo Delay
    g.add_node("delay", "dly1", x=900, y=160, params={"time_sec": 0.4, "feedback": 0.5, "mix": 0.35, "ping_pong": True})

    # Reverb
    g.add_node("reverb", "rev1", x=1100, y=160, params={"room_size": 0.85, "damping": 0.3, "wet": 0.5, "dry": 0.6})

    # Master Output
    g.add_node("audio_output", "out1", x=1320, y=160, params={"master_volume": 0.85, "limiter_enabled": True})

    g.connect("osc1", "out", "mix1", "in1")
    g.connect("osc2", "out", "mix1", "in2")
    g.connect("mix1", "out", "flt1", "in")
    g.connect("flt1", "out", "vca1", "in")
    g.connect("env1", "out", "vca1", "cv")
    g.connect("vca1", "out", "dly1", "in_l")
    g.connect("vca1", "out", "dly1", "in_r")
    g.connect("dly1", "out_l", "rev1", "in_l")
    g.connect("dly1", "out_r", "rev1", "in_r")
    g.connect("rev1", "out_l", "out1", "left")
    g.connect("rev1", "out_r", "out1", "right")

    return g


def create_fm_bell_patch() -> NodeGraph:
    """2-operator Frequency Modulation electric piano / bell synth."""
    g = NodeGraph(name="FM Crystal Bell", sample_rate=44100, block_size=128)

    # Modulator (Frequency ratio 3.5x)
    g.add_node("oscillator", "mod_osc", x=60, y=100, params={"waveform": "sine", "frequency": 1540.0})
    # Modulator Envelope
    g.add_node("adsr", "mod_env", x=60, y=300, params={"attack": 0.001, "decay": 0.45, "sustain": 0.0, "release": 0.3})
    # Modulator VCA (controls modulation index)
    g.add_node("vca", "mod_vca", x=280, y=100, params={"gain": 2.5})

    # Carrier oscillator (Sine)
    g.add_node("oscillator", "carrier_osc", x=500, y=100, params={"waveform": "sine", "frequency": 440.0})

    # Carrier Envelope
    g.add_node("adsr", "carrier_env", x=500, y=300, params={"attack": 0.002, "decay": 1.2, "sustain": 0.1, "release": 0.8})
    # Carrier VCA
    g.add_node("vca", "carrier_vca", x=720, y=100, params={"gain": 0.9})

    # Reverb
    g.add_node("reverb", "rev1", x=940, y=100, params={"room_size": 0.75, "damping": 0.25, "wet": 0.4, "dry": 0.7})

    # Master Out
    g.add_node("audio_output", "out1", x=1160, y=100, params={"master_volume": 0.85, "limiter_enabled": True})

    g.connect("mod_osc", "out", "mod_vca", "in")
    g.connect("mod_env", "out", "mod_vca", "cv")
    g.connect("mod_vca", "out", "carrier_osc", "pm")
    g.connect("carrier_osc", "out", "carrier_vca", "in")
    g.connect("carrier_env", "out", "carrier_vca", "cv")
    g.connect("carrier_vca", "out", "rev1", "in_l")
    g.connect("carrier_vca", "out", "rev1", "in_r")
    g.connect("rev1", "out_l", "out1", "left")
    g.connect("rev1", "out_r", "out1", "right")

    return g


PRESET_CATALOG: Dict[str, Callable[[], NodeGraph]] = {
    "acid_303": create_acid_303_patch,
    "sub_bass": create_sub_bass_patch,
    "lush_pad": create_lush_pad_patch,
    "fm_bell": create_fm_bell_patch,
}
