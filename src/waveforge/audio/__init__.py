"""Audio I/O, MIDI handling, and playback drivers."""

from waveforge.audio.wav_io import write_wav, read_wav, get_wav_bytes
from waveforge.audio.midi import (
    midi_to_freq,
    freq_to_midi,
    note_name_to_midi,
    midi_to_note_name,
    SCALES,
)
from waveforge.audio.player import AudioPlayer

__all__ = [
    "write_wav",
    "read_wav",
    "get_wav_bytes",
    "midi_to_freq",
    "freq_to_midi",
    "note_name_to_midi",
    "midi_to_note_name",
    "SCALES",
    "AudioPlayer",
]
