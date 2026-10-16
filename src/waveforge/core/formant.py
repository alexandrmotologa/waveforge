"""Triple-peak formant vowel filter modeled on human vocal tract acoustic resonances."""

from __future__ import annotations
import math
import numpy as np
from typing import Dict, Tuple, List, Optional
from waveforge.core.config import FilterType
from waveforge.core.filters import BiquadFilter


# Standard formant frequencies (Hz), bandwidth Q, and relative gain (dB) for adult vocal tract
VOWEL_FORMANTS: Dict[str, List[Tuple[float, float, float]]] = {
    "A": [(800.0, 5.0, 0.0), (1200.0, 6.0, -4.0), (2800.0, 8.0, -12.0)],
    "E": [(500.0, 4.5, 0.0), (1800.0, 7.0, -6.0), (2500.0, 8.0, -14.0)],
    "I": [(270.0, 4.0, 0.0), (2300.0, 8.0, -8.0), (3000.0, 9.0, -16.0)],
    "O": [(450.0, 4.5, 0.0), (800.0, 5.5, -7.0), (2500.0, 8.0, -15.0)],
    "U": [(300.0, 4.0, 0.0), (870.0, 5.5, -9.0), (2250.0, 8.0, -18.0)],
}

VOWEL_LIST = ["A", "E", "I", "O", "U"]


class FormantFilter:
    """Triple-peak bandpass vowel filter with continuous interpolation between phonemes."""

    def __init__(
        self,
        sample_rate: int = 44100,
        vowel_pos: float = 0.0,  # 0.0=A, 1.0=E, 2.0=I, 3.0=O, 4.0=U
        resonance_scale: float = 1.0,
    ):
        self.sample_rate = float(sample_rate)
        self.vowel_pos = max(0.0, min(4.0, float(vowel_pos)))
        self.resonance_scale = max(0.2, min(5.0, float(resonance_scale)))

        # 3 parallel bandpass filters
        self.f1 = BiquadFilter(sample_rate=sample_rate, filter_type=FilterType.BANDPASS)
        self.f2 = BiquadFilter(sample_rate=sample_rate, filter_type=FilterType.BANDPASS)
        self.f3 = BiquadFilter(sample_rate=sample_rate, filter_type=FilterType.BANDPASS)

        self.g1 = 1.0
        self.g2 = 0.5
        self.g3 = 0.25

        self._update_formants()

    def set_sample_rate(self, sr: int) -> None:
        self.sample_rate = float(sr)
        self.f1.set_sample_rate(sr)
        self.f2.set_sample_rate(sr)
        self.f3.set_sample_rate(sr)
        self._update_formants()

    def set_vowel(self, pos: float) -> None:
        self.vowel_pos = max(0.0, min(4.0, float(pos)))
        self._update_formants()

    def _update_formants(self) -> None:
        pos = self.vowel_pos
        idx0 = int(math.floor(pos))
        idx1 = min(4, idx0 + 1)
        frac = pos - idx0

        v0 = VOWEL_FORMANTS[VOWEL_LIST[idx0]]
        v1 = VOWEL_FORMANTS[VOWEL_LIST[idx1]]

        # Interpolate F1, F2, F3 frequencies, Q, and gain
        freqs = []
        qs = []
        gains = []
        for p in range(3):
            f = v0[p][0] + frac * (v1[p][0] - v0[p][0])
            q = (v0[p][1] + frac * (v1[p][1] - v0[p][1])) * self.resonance_scale
            g_db = v0[p][2] + frac * (v1[p][2] - v0[p][2])
            freqs.append(f)
            qs.append(q)
            gains.append(10.0 ** (g_db / 20.0))

        self.f1.set_params(cutoff_hz=freqs[0], q=qs[0])
        self.f2.set_params(cutoff_hz=freqs[1], q=qs[1])
        self.f3.set_params(cutoff_hz=freqs[2], q=qs[2])

        self.g1 = gains[0]
        self.g2 = gains[1]
        self.g3 = gains[2]

    def reset_state(self) -> None:
        self.f1.reset_state()
        self.f2.reset_state()
        self.f3.reset_state()

    def process_sample(self, x: float) -> float:
        """Process sample through parallel formant peaks and sum."""
        y1 = self.f1.process_sample(x) * self.g1
        y2 = self.f2.process_sample(x) * self.g2
        y3 = self.f3.process_sample(x) * self.g3
        return y1 + y2 + y3

    def process_block(
        self,
        input_block: np.ndarray,
        vowel_mod: Optional[np.ndarray] = None,
        output_block: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        n = len(input_block)
        if output_block is None:
            output_block = np.zeros(n, dtype=np.float32)

        has_mod = vowel_mod is not None
        base_vowel = self.vowel_pos

        for i in range(n):
            if has_mod:
                dyn_pos = max(0.0, min(4.0, base_vowel + float(vowel_mod[i])))
                self.vowel_pos = dyn_pos
                self._update_formants()

            output_block[i] = self.process_sample(float(input_block[i]))

        return output_block
