"""Polyphonic voice allocator, voice stealing, and unison detune engine."""

from __future__ import annotations
import copy
import math
import numpy as np
from typing import List, Tuple, Optional
from waveforge.graph.patch import NodeGraph
from waveforge.graph.engine import AudioEngine, midi_to_freq


class SynthVoice:
    """Single polyphonic voice instance running a clone of the patch graph."""

    def __init__(self, voice_id: int, graph: NodeGraph):
        self.voice_id = voice_id
        # Deepcopy graph so parameters and state are fully independent per voice
        self.graph = NodeGraph.from_schema(graph.to_schema())
        self.engine = AudioEngine(self.graph)
        self.active_note = -1
        self.velocity = 0.0
        self.age = 0
        self.is_releasing = False

    def note_on(self, note: int, velocity: float) -> None:
        self.active_note = note
        self.velocity = velocity
        self.age = 0
        self.is_releasing = False
        self.engine.note_on(note, velocity)

    def note_off(self) -> None:
        self.is_releasing = True
        self.engine.note_off()

    def is_free(self) -> bool:
        return self.active_note == -1

    def process_block(self) -> Tuple[np.ndarray, np.ndarray]:
        self.age += 1
        return self.engine.process_block()


class PolyVoiceManager:
    """Polyphonic synthesizer voice manager with voice stealing and unison spread."""

    def __init__(
        self,
        base_graph: NodeGraph,
        max_voices: int = 8,
        unison_mode: bool = False,
        unison_detune_cents: float = 12.0,
    ):
        self.base_graph = base_graph
        self.max_voices = max(1, min(16, max_voices))
        self.unison_mode = unison_mode
        self.unison_detune_cents = unison_detune_cents

        self.voices: List[SynthVoice] = [
            SynthVoice(i, base_graph) for i in range(self.max_voices)
        ]
        self._note_voice_map: dict[int, list[int]] = {}

    def note_on(self, midi_note: int, velocity: float = 0.85) -> None:
        """Allocate voice(s) for incoming note on."""
        if self.unison_mode:
            # Trigger all voices on same note with spread detuning
            detune_spread = np.linspace(-self.unison_detune_cents, self.unison_detune_cents, self.max_voices)
            for i, voice in enumerate(self.voices):
                cents = detune_spread[i]
                freq = midi_to_freq(midi_note) * (2.0 ** (cents / 1200.0))
                voice.note_on(midi_note, velocity)
                # Apply detuned frequency to oscillators in this voice
                for node in voice.graph.nodes.values():
                    if hasattr(node, "params") and "frequency" in node.params:
                        node.params["frequency"] = freq
            self._note_voice_map[midi_note] = list(range(self.max_voices))
            return

        # Polyphonic mode: find free voice or steal oldest
        allocated_voice = None

        # 1. Search for completely free voice
        for v in self.voices:
            if v.is_free():
                allocated_voice = v
                break

        # 2. Search for voice in release stage
        if allocated_voice is None:
            releasing_voices = [v for v in self.voices if v.is_releasing]
            if releasing_voices:
                allocated_voice = max(releasing_voices, key=lambda v: v.age)

        # 3. Voice stealing: steal oldest active voice
        if allocated_voice is None:
            allocated_voice = max(self.voices, key=lambda v: v.age)

        allocated_voice.note_on(midi_note, velocity)
        self._note_voice_map.setdefault(midi_note, []).append(allocated_voice.voice_id)

    def note_off(self, midi_note: int) -> None:
        """Trigger release stage on voice(s) playing this note."""
        voice_ids = self._note_voice_map.pop(midi_note, [])
        for vid in voice_ids:
            if vid < len(self.voices):
                self.voices[vid].note_off()

    def process_block(self) -> Tuple[np.ndarray, np.ndarray]:
        """Evaluate all active voices and sum into master stereo bus."""
        bs = self.base_graph.block_size
        master_l = np.zeros(bs, dtype=np.float32)
        master_r = np.zeros(bs, dtype=np.float32)

        for v in self.voices:
            vl, vr = v.process_block()
            master_l += vl
            master_r += vr

        # Normalize by active voices or soft clamp to prevent clipping
        if self.unison_mode:
            master_l *= (1.0 / math.sqrt(self.max_voices))
            master_r *= (1.0 / math.sqrt(self.max_voices))

        return np.tanh(master_l), np.tanh(master_r)

    def render(
        self,
        duration_sec: float = 3.0,
        notes: Optional[List[Tuple[float, float, int, float]]] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Render polyphonic score offline.

        Args:
            duration_sec: Total duration to render.
            notes: List of (start_sec, end_sec, midi_note, velocity).
                   If None, plays a default major triad (C4, E4, G4).
        """
        sr = self.base_graph.sample_rate
        bs = self.base_graph.block_size
        total_samples = int(duration_sec * sr)
        num_blocks = math.ceil(total_samples / bs)

        if notes is None:
            # Default polyphonic chord: C major triad
            notes = [
                (0.0, duration_sec * 0.75, 60, 0.8),  # C4
                (0.0, duration_sec * 0.75, 64, 0.8),  # E4
                (0.0, duration_sec * 0.75, 67, 0.8),  # G4
            ]

        left_full = np.zeros(num_blocks * bs, dtype=np.float32)
        right_full = np.zeros(num_blocks * bs, dtype=np.float32)

        active_events = sorted(notes, key=lambda x: x[0])
        note_on_queue = list(active_events)
        note_off_queue = sorted(notes, key=lambda x: x[1])

        for b in range(num_blocks):
            cur_time = (b * bs) / sr

            # Process Note On
            while note_on_queue and note_on_queue[0][0] <= cur_time:
                _, _, n, vel = note_on_queue.pop(0)
                self.note_on(n, vel)

            # Process Note Off
            while note_off_queue and note_off_queue[0][1] <= cur_time:
                _, _, n, _ = note_off_queue.pop(0)
                self.note_off(n)

            bl_l, bl_r = self.process_block()
            offset = b * bs
            left_full[offset : offset + bs] = bl_l
            right_full[offset : offset + bs] = bl_r

        return left_full[:total_samples], right_full[:total_samples]
