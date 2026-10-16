"""MIDI note calculation, equal-temperament tuning, and musical scales."""

from __future__ import annotations
import math
from typing import Dict, List


NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def midi_to_freq(note: int, tuning_a4: float = 440.0) -> float:
    """Convert standard MIDI note number [0, 127] to frequency in Hz."""
    return tuning_a4 * (2.0 ** ((note - 69) / 12.0))


def freq_to_midi(freq: float, tuning_a4: float = 440.0) -> int:
    """Convert frequency in Hz to nearest MIDI note number."""
    if freq <= 0.0:
        return 0
    return round(69.0 + 12.0 * math.log2(freq / tuning_a4))


def note_name_to_midi(name: str) -> int:
    """Convert note name like 'C4', 'A#3', 'Gb2' to MIDI note number."""
    name = name.strip()
    if not name:
        return 60  # Default Middle C

    # Handle accidentals
    note_part = name[:-1] if name[-1].isdigit() or name[-1] == '-' else name
    octave_str = name[len(note_part):]
    octave = int(octave_str) if octave_str else 4

    note_part = note_part.upper()
    if note_part.endswith("B"):
        # Flat: e.g. Bb -> A#
        base = note_part[0]
        flats = {"DB": "C#", "EB": "D#", "GB": "F#", "AB": "G#", "BB": "A#"}
        note_part = flats.get(note_part, note_part)

    try:
        semitone = NOTE_NAMES.index(note_part)
        return (octave + 1) * 12 + semitone
    except ValueError:
        return 60


def midi_to_note_name(note: int) -> str:
    """Convert MIDI note number to note name string (e.g. 60 -> 'C4')."""
    octave = (note // 12) - 1
    semitone = note % 12
    return f"{NOTE_NAMES[semitone]}{octave}"


SCALES: Dict[str, List[int]] = {
    "chromatic": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "pentatonic_major": [0, 2, 4, 7, 9],
    "pentatonic_minor": [0, 3, 5, 7, 10],
    "blues": [0, 3, 5, 6, 7, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
}
