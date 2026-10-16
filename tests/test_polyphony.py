"""Unit tests for polyphonic voice allocation, voice stealing, and unison detuning."""

import numpy as np
import pytest
from waveforge.graph.presets import create_lush_pad_patch, create_acid_303_patch
from waveforge.graph.polyphony import PolyVoiceManager


def test_polyphonic_voice_allocation():
    """Verify that multiple notes are allocated to distinct voices."""
    graph = create_lush_pad_patch()
    poly = PolyVoiceManager(base_graph=graph, max_voices=4)

    assert len(poly.voices) == 4
    for v in poly.voices:
        assert v.is_free()

    # Play two notes
    poly.note_on(60, 0.8)
    poly.note_on(64, 0.8)

    occupied = [v for v in poly.voices if not v.is_free()]
    assert len(occupied) == 2

    # Release note 60
    poly.note_off(60)
    assert 60 not in poly._note_voice_map


def test_voice_stealing_when_exhausted():
    """Verify oldest voice is stolen when max polyphony voice limit is exceeded."""
    graph = create_acid_303_patch()
    # 2 voices only
    poly = PolyVoiceManager(base_graph=graph, max_voices=2)

    poly.note_on(60, 0.8)
    poly.process_block()  # Age voices
    poly.note_on(62, 0.8)
    poly.process_block()  # Age voices

    # Both voices occupied
    assert all(not v.is_free() for v in poly.voices)

    # Note 60 is oldest; now trigger note 64 -> should steal oldest voice
    poly.note_on(64, 0.8)

    active_notes = [v.active_note for v in poly.voices]
    assert 64 in active_notes


def test_unison_detune_mode():
    """Verify unison mode triggers all voices simultaneously with detuning."""
    graph = create_lush_pad_patch()
    poly = PolyVoiceManager(base_graph=graph, max_voices=4, unison_mode=True, unison_detune_cents=15.0)

    poly.note_on(60, 0.9)
    # All 4 voices should be triggered
    for v in poly.voices:
        assert v.active_note == 60

    bl_l, bl_r = poly.process_block()
    assert len(bl_l) == graph.block_size
    assert np.isfinite(bl_l).all()
    assert np.isfinite(bl_r).all()
    assert np.max(np.abs(bl_l)) > 0.0


def test_polyphonic_score_render():
    """Verify offline rendering of polyphonic chord progression."""
    graph = create_lush_pad_patch()
    poly = PolyVoiceManager(base_graph=graph, max_voices=6)

    # Render 0.5s C major triad
    score = [
        (0.0, 0.4, 60, 0.8),  # C4
        (0.0, 0.4, 64, 0.8),  # E4
        (0.0, 0.4, 67, 0.8),  # G4
    ]

    left, right = poly.render(duration_sec=0.5, notes=score)
    expected_len = int(0.5 * graph.sample_rate)

    assert len(left) == expected_len
    assert len(right) == expected_len
    assert np.isfinite(left).all()
    assert np.isfinite(right).all()
    assert np.max(np.abs(left)) > 0.01
