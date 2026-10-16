"""Analog-modeled exponential ADSR (Attack, Decay, Sustain, Release) envelope generator."""

from __future__ import annotations
import math
import numpy as np
from typing import Optional
from waveforge.core.config import EnvelopeStage


class ADSREnvelope:
    """Analog-modeled exponential ADSR envelope generator using RC charging equations."""

    def __init__(
        self,
        sample_rate: int = 44100,
        attack: float = 0.01,    # seconds
        decay: float = 0.1,     # seconds
        sustain: float = 0.7,   # level [0.0, 1.0]
        release: float = 0.2,   # seconds
    ):
        self.sample_rate = float(sample_rate)
        self.attack_time = max(0.0005, float(attack))
        self.decay_time = max(0.0005, float(decay))
        self.sustain_level = max(0.0, min(1.0, float(sustain)))
        self.release_time = max(0.0005, float(release))

        self.stage = EnvelopeStage.IDLE
        self.current_value = 0.0
        self._gate = False

        self._update_coefficients()

    def set_sample_rate(self, sr: int) -> None:
        self.sample_rate = float(sr)
        self._update_coefficients()

    def set_params(
        self,
        attack: Optional[float] = None,
        decay: Optional[float] = None,
        sustain: Optional[float] = None,
        release: Optional[float] = None,
    ) -> None:
        if attack is not None:
            self.attack_time = max(0.0005, float(attack))
        if decay is not None:
            self.decay_time = max(0.0005, float(decay))
        if sustain is not None:
            self.sustain_level = max(0.0, min(1.0, float(sustain)))
        if release is not None:
            self.release_time = max(0.0005, float(release))
        self._update_coefficients()

    def _update_coefficients(self) -> None:
        # Analog RC charging curves:
        # Attack targets 1.5 so that reaching 1.0 has a punchy, musical curve
        self._attack_target = 1.5
        self._attack_coef = math.exp(-1.0 / (self.attack_time * self.sample_rate * 0.36))

        # Decay targets sustain level
        self._decay_coef = math.exp(-1.0 / (self.decay_time * self.sample_rate * 0.25))

        # Release targets slightly below 0 (-0.05) to cleanly hit 0 without infinite tail
        self._release_target = -0.05
        self._release_coef = math.exp(-1.0 / (self.release_time * self.sample_rate * 0.25))

    def gate_on(self) -> None:
        """Trigger note on / gate high."""
        self._gate = True
        self.stage = EnvelopeStage.ATTACK

    def gate_off(self) -> None:
        """Trigger note off / gate low."""
        self._gate = False
        if self.stage != EnvelopeStage.IDLE:
            self.stage = EnvelopeStage.RELEASE

    def reset(self) -> None:
        self.stage = EnvelopeStage.IDLE
        self.current_value = 0.0
        self._gate = False

    def is_active(self) -> bool:
        return self.stage != EnvelopeStage.IDLE or self.current_value > 1e-4

    def process_sample(self, gate: Optional[bool] = None) -> float:
        """Process single envelope sample."""
        if gate is not None:
            if gate and not self._gate:
                self.gate_on()
            elif not gate and self._gate:
                self.gate_off()

        if self.stage == EnvelopeStage.IDLE:
            self.current_value = 0.0
            return 0.0

        elif self.stage == EnvelopeStage.ATTACK:
            self.current_value = self._attack_target + (self.current_value - self._attack_target) * self._attack_coef
            if self.current_value >= 1.0:
                self.current_value = 1.0
                self.stage = EnvelopeStage.DECAY

        elif self.stage == EnvelopeStage.DECAY:
            target = self.sustain_level
            self.current_value = target + (self.current_value - target) * self._decay_coef
            if abs(self.current_value - target) <= 1e-3:
                self.current_value = target
                self.stage = EnvelopeStage.SUSTAIN

        elif self.stage == EnvelopeStage.SUSTAIN:
            self.current_value = self.sustain_level

        elif self.stage == EnvelopeStage.RELEASE:
            self.current_value = self._release_target + (self.current_value - self._release_target) * self._release_coef
            if self.current_value <= 0.0:
                self.current_value = 0.0
                self.stage = EnvelopeStage.IDLE

        return float(self.current_value)

    def process_block(
        self,
        num_samples: int,
        gate_vector: Optional[np.ndarray] = None,
        output: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """Process a block of envelope output samples."""
        if output is None:
            output = np.zeros(num_samples, dtype=np.float32)

        has_gate = gate_vector is not None
        for i in range(num_samples):
            g = bool(gate_vector[i] > 0.5) if has_gate else None
            output[i] = self.process_sample(g)

        return output
