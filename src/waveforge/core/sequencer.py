"""16-Step Modular Sequencer with Pitch CV, Gate, Velocity, Accent, and 303-style Slide."""

from __future__ import annotations
import math
import numpy as np
from typing import List, Tuple, Optional


class SequencerStep:
    def __init__(
        self,
        pitch: float = 60.0,   # MIDI note number
        gate: bool = True,
        velocity: float = 0.8,
        slide: bool = False,
        accent: bool = False,
    ):
        self.pitch = float(pitch)
        self.gate = bool(gate)
        self.velocity = float(velocity)
        self.slide = bool(slide)
        self.accent = bool(accent)


class StepSequencer:
    """16-Step modular pattern sequencer with portamento slide and accent dynamics."""

    def __init__(
        self,
        sample_rate: int = 44100,
        bpm: float = 125.0,
        steps: Optional[List[SequencerStep]] = None,
        division: int = 16,  # 1/16th notes
        gate_length: float = 0.65,  # 65% of step duration
        slide_time: float = 0.06,   # 60ms portamento time
    ):
        self.sample_rate = float(sample_rate)
        self.bpm = max(20.0, min(300.0, float(bpm)))
        self.division = division
        self.gate_length = max(0.05, min(0.95, float(gate_length)))
        self.slide_time = max(0.005, min(0.2, float(slide_time)))

        if steps is not None and len(steps) == 16:
            self.steps = steps
        else:
            # Default classic acid bassline pattern
            default_pitches = [36, 36, 48, 36, 39, 36, 48, 46, 36, 39, 41, 42, 41, 39, 36, 34]
            default_gates =   [1,  1,  1,  0,  1,  1,  1,  1,  1,  0,  1,  1,  1,  1,  1,  0]
            default_slides =  [0,  0,  1,  0,  0,  0,  1,  0,  0,  0,  0,  1,  0,  0,  0,  0]
            default_accents = [1,  0,  1,  0,  0,  0,  1,  0,  0,  0,  1,  0,  1,  0,  0,  0]
            self.steps = [
                SequencerStep(
                    pitch=default_pitches[i],
                    gate=bool(default_gates[i]),
                    velocity=0.8,
                    slide=bool(default_slides[i]),
                    accent=bool(default_accents[i]),
                )
                for i in range(16)
            ]

        self.current_step = 0
        self._sample_counter = 0
        self._current_pitch = self.steps[0].pitch
        self._target_pitch = self.steps[0].pitch
        self._current_gate = 0.0
        self._current_accent = 0.0

    def set_sample_rate(self, sr: int) -> None:
        self.sample_rate = float(sr)

    def set_bpm(self, bpm: float) -> None:
        self.bpm = max(20.0, min(300.0, float(bpm)))

    def reset(self) -> None:
        self.current_step = 0
        self._sample_counter = 0
        self._current_pitch = self.steps[0].pitch
        self._target_pitch = self.steps[0].pitch
        self._current_gate = 0.0
        self._current_accent = 0.0

    def samples_per_step(self) -> int:
        """Calculate sample duration per 16th note step based on BPM."""
        beats_per_sec = self.bpm / 60.0
        # 1 beat = 1/4 note = 4 sixteenth notes
        steps_per_sec = beats_per_sec * (self.division / 4.0)
        return int(round(self.sample_rate / steps_per_sec))

    def process_sample(self, clock_pulse: Optional[float] = None) -> Tuple[float, float, float]:
        """Advance sequencer by one sample.

        Returns:
            Tuple of (frequency_hz, gate_cv, accent_cv)
        """
        step_len = self.samples_per_step()
        gate_samples = int(step_len * self.gate_length)

        # Check step boundary
        if self._sample_counter >= step_len:
            self._sample_counter = 0
            self.current_step = (self.current_step + 1) % 16

        step = self.steps[self.current_step]
        self._target_pitch = step.pitch

        # Gate calculation
        if step.gate and self._sample_counter < gate_samples:
            self._current_gate = 1.0 * step.velocity
        else:
            self._current_gate = 0.0

        # Accent
        self._current_accent = 1.0 if (step.accent and self._current_gate > 0.0) else 0.0

        # Slide / Portamento smoothing
        if step.slide:
            slide_coef = math.exp(-1.0 / (self.slide_time * self.sample_rate))
            self._current_pitch = self._target_pitch + (self._current_pitch - self._target_pitch) * slide_coef
        else:
            self._current_pitch = self._target_pitch

        self._sample_counter += 1

        # Convert MIDI pitch to Hz: f = 440 * 2^((p - 69) / 12)
        freq_hz = 440.0 * (2.0 ** ((self._current_pitch - 69.0) / 12.0))
        return freq_hz, self._current_gate, self._current_accent
