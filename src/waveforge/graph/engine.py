"""High-throughput modular DSP execution engine and block-based DAG evaluator."""

from __future__ import annotations
import math
import numpy as np
from typing import Dict, Tuple, Optional, List, Any
from waveforge.graph.patch import NodeGraph
from waveforge.graph.node import (
    BaseNode,
    OutputNode,
    OscillatorNode,
    ADSRNode,
    KarplusStrongNode,
    KickNode,
    SnareNode,
    HiHatNode,
)


def midi_to_freq(note: int, tuning_a4: float = 440.0) -> float:
    """Convert MIDI note number [0, 127] to frequency in Hz."""
    return tuning_a4 * (2.0 ** ((note - 69) / 12.0))


class AudioEngine:
    """Real-time block DSP evaluator for NodeGraph patches."""

    def __init__(self, graph: NodeGraph):
        self.graph = graph
        self.sample_rate = graph.sample_rate
        self.block_size = graph.block_size

        # Execution order from DAG topological sort
        self.execution_order: List[str] = []

        # Preallocated block buffers: (node_id, pin_name) -> np.ndarray
        self.buffers: Dict[Tuple[str, str], np.ndarray] = {}

        # Connection lookup: (to_node, to_pin) -> (from_node, from_pin)
        self.wiring: Dict[Tuple[str, str], Tuple[str, str]] = {}

        self.rebuild()

    def rebuild(self) -> None:
        """Recompute topological execution order and reallocate wire buffers."""
        self.execution_order = self.graph.get_topological_sort()
        self.wiring.clear()
        for c in self.graph.connections:
            self.wiring[(c.to_node, c.to_pin)] = (c.from_node, c.from_pin)

        # Allocate output buffers for all nodes
        self.buffers.clear()
        for node_id, node in self.graph.nodes.items():
            for pin_name in node.output_pins:
                self.buffers[(node_id, pin_name)] = np.zeros(self.block_size, dtype=np.float32)

    def note_on(self, midi_note: int, velocity: float = 0.8) -> None:
        """Trigger note on: updates oscillator frequencies and opens ADSR envelopes."""
        freq = midi_to_freq(midi_note)
        for node in self.graph.nodes.values():
            if isinstance(node, OscillatorNode):
                node.params["frequency"] = freq
            elif isinstance(node, ADSRNode):
                node.env.gate_on()
            elif isinstance(node, KarplusStrongNode):
                node.params["frequency"] = freq
                node.string.set_frequency(freq)
                node.string.trigger_pluck(velocity)
            elif isinstance(node, KickNode):
                node.kick.trigger(velocity)
            elif isinstance(node, SnareNode):
                node.snare.trigger(velocity)
            elif isinstance(node, HiHatNode):
                node.hihat.trigger(velocity)

    def note_off(self) -> None:
        """Trigger note off: closes ADSR envelopes into release stage."""
        for node in self.graph.nodes.values():
            if isinstance(node, ADSRNode):
                node.env.gate_off()

    def set_param(self, node_id: str, param_name: str, value: Any) -> None:
        """Update parameter value on a specific node."""
        if node_id in self.graph.nodes:
            self.graph.nodes[node_id].set_param(param_name, value)

    def reset_state(self) -> None:
        """Reset internal filter delays, phase accumulators, and envelopes."""
        for node in self.graph.nodes.values():
            node.reset_state()
        for buf in self.buffers.values():
            buf.fill(0.0)

    def process_block(self) -> Tuple[np.ndarray, np.ndarray]:
        """Evaluate one block of audio through the entire node DAG.

        Returns:
            Tuple of (left_channel_block, right_channel_block)
        """
        bs = self.block_size
        master_left = np.zeros(bs, dtype=np.float32)
        master_right = np.zeros(bs, dtype=np.float32)

        for node_id in self.execution_order:
            node = self.graph.nodes.get(node_id)
            if node is None:
                continue

            # Gather input buffers
            node_inputs: Dict[str, np.ndarray] = {}
            for in_pin_name, pin in node.input_pins.items():
                wire_key = (node_id, in_pin_name)
                if wire_key in self.wiring:
                    src_node, src_pin = self.wiring[wire_key]
                    src_buf = self.buffers.get((src_node, src_pin))
                    if src_buf is not None:
                        node_inputs[in_pin_name] = src_buf
                else:
                    # Provide default static buffer if disconnected
                    if pin.default_value != 0.0:
                        default_buf = np.full(bs, pin.default_value, dtype=np.float32)
                        node_inputs[in_pin_name] = default_buf

            # Process node
            outputs = node.process(bs, node_inputs)

            # Store outputs
            for out_pin_name, out_data in outputs.items():
                buf_key = (node_id, out_pin_name)
                if buf_key in self.buffers:
                    np.copyto(self.buffers[buf_key], out_data)

            # Accumulate if OutputNode
            if isinstance(node, OutputNode):
                master_left += outputs.get("left", np.zeros(bs, dtype=np.float32))
                master_right += outputs.get("right", np.zeros(bs, dtype=np.float32))

        return master_left, master_right

    def render(
        self,
        duration_sec: float = 3.0,
        midi_note: Optional[int] = 60,
        velocity: float = 0.8,
        note_duration_sec: Optional[float] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Render complete audio file offline.

        Args:
            duration_sec: Total duration to render in seconds.
            midi_note: Optional MIDI note to trigger at start.
            velocity: Note velocity in [0.0, 1.0].
            note_duration_sec: How long note is held before note_off (defaults to 75% duration).
        """
        self.reset_state()

        if note_duration_sec is None:
            note_duration_sec = duration_sec * 0.75

        total_samples = int(duration_sec * self.sample_rate)
        num_blocks = math.ceil(total_samples / self.block_size)
        note_off_sample = int(note_duration_sec * self.sample_rate)

        left_full = np.zeros(num_blocks * self.block_size, dtype=np.float32)
        right_full = np.zeros(num_blocks * self.block_size, dtype=np.float32)

        if midi_note is not None:
            self.note_on(midi_note, velocity)

        note_off_sent = False

        for b in range(num_blocks):
            sample_offset = b * self.block_size

            # Check if note off should be triggered
            if (
                midi_note is not None
                and not note_off_sent
                and sample_offset >= note_off_sample
            ):
                self.note_off()
                note_off_sent = True

            bl_left, bl_right = self.process_block()
            left_full[sample_offset : sample_offset + self.block_size] = bl_left
            right_full[sample_offset : sample_offset + self.block_size] = bl_right

        # Trim to exact requested length
        return left_full[:total_samples], right_full[:total_samples]
