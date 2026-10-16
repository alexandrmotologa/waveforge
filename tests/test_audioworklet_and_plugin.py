"""Unit tests for WebAudio / AudioWorklet player and VST3 / CLAP plugin code generation."""

import os
import tempfile
import pytest
from waveforge.graph.presets import create_acid_303_patch, create_techno_acid_seq_patch
from waveforge.codegen.audioworklet_generator import AudioWorkletGenerator, WebAudioPlayerGenerator
from waveforge.codegen.plugin_generator import PluginGenerator


def test_webaudio_player_generator():
    """Verify standalone HTML5 + WebAudio player generation."""
    graph = create_acid_303_patch()
    gen = AudioWorkletGenerator(graph)

    html = gen.generate_html_player()
    assert "<!DOCTYPE html>" in html
    assert "AudioContext" in html
    assert "WaveForge Standalone Player" in html
    assert "playNote" in html
    assert "white-key" in html

    # Alias check
    alias_html = gen.generate_standalone_html(title="Custom Synth")
    assert "<!DOCTYPE html>" in alias_html


def test_plugin_generator_cmake():
    """Verify CMakeLists.txt generation for VST3 and CLAP plugin targets."""
    graph = create_acid_303_patch()
    p_gen = PluginGenerator(graph)

    cmake = p_gen.generate_cmake(plugin_name="AcidSynth303")
    assert "project(AcidSynth303" in cmake
    assert "CMAKE_CXX_STANDARD 20" in cmake
    assert "add_library(AcidSynth303 MODULE" in cmake
    assert "waveforge_synth.h" in cmake


def test_plugin_generator_cpp_code():
    """Verify C++ header and source implementation generation."""
    graph = create_acid_303_patch()
    p_gen = PluginGenerator(graph)

    header = p_gen.generate_cpp_header(plugin_name="AcidSynth303")
    assert "class AcidSynth303Plugin" in header
    assert "void noteOn(int note, float velocity);" in header
    assert "void noteOff(int note);" in header
    assert "void process(const float* const* inputs, float* const* outputs, int numSamples);" in header

    source = p_gen.generate_cpp_source(plugin_name="AcidSynth303")
    assert "AcidSynth303Plugin::AcidSynth303Plugin" in source
    assert "waveforge_synth_process(&m_synth, out_l, out_r, numSamples);" in source
    assert "waveforge_synth_note_on(&m_synth, note, velocity);" in source
    assert "m_parameters.push_back(" in source


def test_plugin_project_export():
    """Verify complete export to directory containing all required plugin files."""
    graph = create_acid_303_patch()
    p_gen = PluginGenerator(graph)

    with tempfile.TemporaryDirectory() as tmpdir:
        files = p_gen.export_plugin_project(output_dir=tmpdir, plugin_name="AcidSynth303")

        assert os.path.exists(files["cmake"])
        assert os.path.exists(files["c_header"])
        assert os.path.exists(files["cpp_header"])
        assert os.path.exists(files["cpp_source"])

        # Check C header is non-empty and valid
        with open(files["c_header"], "r", encoding="utf-8") as f:
            c_code = f.read()
            assert "typedef struct" in c_code
            assert "waveforge_synth_process" in c_code
