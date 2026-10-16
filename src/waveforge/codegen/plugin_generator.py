"""VST3 and CLAP audio plugin wrapper generator for WaveForge synthesizer graphs."""

from __future__ import annotations
import os
import re
from typing import Dict, Any, List
from waveforge.graph.patch import NodeGraph
from waveforge.codegen.c_generator import CCodeGenerator


class PluginGenerator:
    """Generates standard C++ audio plugin project files (VST3 & CLAP) wrapping WaveForge C99 synths."""

    def __init__(self, graph: NodeGraph):
        self.graph = graph

    def _sanitize_name(self, name: str) -> str:
        clean = re.sub(r"[^a-zA-Z0-9_]", "_", name)
        return clean or "WaveForgeSynth"

    def generate_cmake(self, plugin_name: str) -> str:
        """Generate CMakeLists.txt to build the VST3 and CLAP plugin targets."""
        safe_name = self._sanitize_name(plugin_name)
        return f"""cmake_minimum_required(VERSION 3.20)
project({safe_name} VERSION 1.0.0 LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Optimization flags for audio DSP
if(MSVC)
    add_compile_options(/O2 /fp:fast /W4)
else()
    add_compile_options(-O3 -ffast-math -Wall -Wextra)
endif()

# Plugin Sources
set(PLUGIN_SOURCES
    src/{safe_name}_plugin.cpp
    src/{safe_name}_plugin.h
    include/waveforge_synth.h
)

# Standalone shared library / plugin module
add_library({safe_name} MODULE ${{PLUGIN_SOURCES}})

target_include_directories({safe_name} PRIVATE
    ${{CMAKE_CURRENT_SOURCE_DIR}}/include
    ${{CMAKE_CURRENT_SOURCE_DIR}}/src
)

# VST3 and CLAP preprocessor defines
target_compile_definitions({safe_name} PRIVATE
    WAVEFORGE_PLUGIN_NAME="{safe_name}"
    WAVEFORGE_PLUGIN_VENDOR="{self.graph.author or 'WaveForge'}"
    WAVEFORGE_PLUGIN_VERSION="1.0.0"
)

message(STATUS "Configured {safe_name} plugin build target.")
"""

    def generate_cpp_header(self, plugin_name: str) -> str:
        """Generate C++ class header wrapping WaveForge C state and MIDI/Audio buffers."""
        safe_name = self._sanitize_name(plugin_name)
        return f"""#pragma once

#include <cstdint>
#include <string>
#include <vector>
#include "waveforge_synth.h"

namespace waveforge {{

struct ParameterInfo {{
    uint32_t id;
    std::string name;
    std::string unit;
    float min_val;
    float max_val;
    float default_val;
    float current_val;
}};

class {safe_name}Plugin {{
public:
    {safe_name}Plugin(float sample_rate = 44100.0f);
    ~{safe_name}Plugin() = default;

    void setSampleRate(float sampleRate);
    void reset();

    // MIDI Event Handlers
    void noteOn(int note, float velocity);
    void noteOff(int note);
    void pitchBend(float semitones);
    void controlChange(int ccNumber, float value);

    // Parameter Automation
    void setParameter(uint32_t paramId, float normalizedValue);
    float getParameter(uint32_t paramId) const;
    const std::vector<ParameterInfo>& getParameterList() const;

    // Block Processing
    void process(const float* const* inputs, float* const* outputs, int numSamples);

private:
    WaveForgeSynth m_synth;
    float m_sampleRate;
    std::vector<ParameterInfo> m_parameters;

    void initParameters();
}};

}} // namespace waveforge
"""

    def generate_cpp_source(self, plugin_name: str) -> str:
        """Generate C++ class implementation dispatching audio blocks and MIDI."""
        safe_name = self._sanitize_name(plugin_name)

        # Collect exposed parameters from graph nodes
        param_inits: List[str] = []
        param_setters: List[str] = []
        p_id = 0

        for nid, node in self.graph.nodes.items():
            for p_name, p_val in node.params.items():
                if isinstance(p_val, (int, float)) and not isinstance(p_val, bool):
                    v = float(p_val)
                    min_v = 0.0
                    max_v = max(v * 2.0, 1.0)
                    if "cutoff" in p_name:
                        min_v, max_v = 20.0, 20000.0
                    elif "gain" in p_name or "mix" in p_name or "depth" in p_name:
                        min_v, max_v = 0.0, 1.0
                    elif "q" in p_name:
                        min_v, max_v = 0.1, 20.0

                    param_inits.append(
                        f'    m_parameters.push_back({{{p_id}, "{nid}_{p_name}", "", {min_v}f, {max_v}f, {v}f, {v}f}});'
                    )
                    param_setters.append(
                        f'        case {p_id}: m_synth.{nid}_{p_name} = val; break;'
                    )
                    p_id += 1

        inits_str = "\n".join(param_inits) if param_inits else "    // No exposed continuous parameters"
        setters_str = "\n".join(param_setters) if param_setters else "        default: break;"

        return f"""#include "{safe_name}_plugin.h"
#include <algorithm>
#include <cmath>

namespace waveforge {{

{safe_name}Plugin::{safe_name}Plugin(float sample_rate)
    : m_sampleRate(sample_rate) {{
    initParameters();
    reset();
}}

void {safe_name}Plugin::setSampleRate(float sampleRate) {{
    m_sampleRate = sampleRate;
    waveforge_synth_init(&m_synth, m_sampleRate);
}}

void {safe_name}Plugin::reset() {{
    waveforge_synth_init(&m_synth, m_sampleRate);
}}

void {safe_name}Plugin::initParameters() {{
    m_parameters.clear();
{inits_str}
}}

void {safe_name}Plugin::noteOn(int note, float velocity) {{
    waveforge_synth_note_on(&m_synth, note, velocity);
}}

void {safe_name}Plugin::noteOff(int note) {{
    (void)note;
    waveforge_synth_note_off(&m_synth);
}}

void {safe_name}Plugin::pitchBend(float semitones) {{
    (void)semitones;
}}

void {safe_name}Plugin::controlChange(int ccNumber, float value) {{
    (void)ccNumber;
    (void)value;
}}

void {safe_name}Plugin::setParameter(uint32_t paramId, float normalizedValue) {{
    if (paramId >= m_parameters.size()) return;
    float norm = std::clamp(normalizedValue, 0.0f, 1.0f);
    auto& p = m_parameters[paramId];
    float val = p.min_val + norm * (p.max_val - p.min_val);
    p.current_val = val;

    switch (paramId) {{
{setters_str}
        default: break;
    }}
}}

float {safe_name}Plugin::getParameter(uint32_t paramId) const {{
    if (paramId >= m_parameters.size()) return 0.0f;
    const auto& p = m_parameters[paramId];
    if (p.max_val <= p.min_val) return 0.0f;
    return (p.current_val - p.min_val) / (p.max_val - p.min_val);
}}

const std::vector<ParameterInfo>& {safe_name}Plugin::getParameterList() const {{
    return m_parameters;
}}

void {safe_name}Plugin::process(const float* const* inputs, float* const* outputs, int numSamples) {{
    (void)inputs;
    if (!outputs || !outputs[0]) return;

    float* out_l = outputs[0];
    float* out_r = outputs[1] ? outputs[1] : outputs[0];

    waveforge_synth_process(&m_synth, out_l, out_r, numSamples);
}}

}} // namespace waveforge
"""

    def export_plugin_project(self, output_dir: str, plugin_name: str = "WaveForgeSynth") -> Dict[str, str]:
        """Export complete CMake + C++ plugin project directory."""
        safe_name = self._sanitize_name(plugin_name)
        os.makedirs(os.path.join(output_dir, "include"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "src"), exist_ok=True)

        # 1. Standalone C99 DSP core header
        c_gen = CCodeGenerator(self.graph)
        c_header = c_gen.generate_header(guard_name=f"{safe_name.upper()}_SYNTH_H")
        c_header_path = os.path.join(output_dir, "include", "waveforge_synth.h")
        with open(c_header_path, "w", encoding="utf-8") as f:
            f.write(c_header)

        # 2. CMakeLists.txt
        cmake = self.generate_cmake(safe_name)
        cmake_path = os.path.join(output_dir, "CMakeLists.txt")
        with open(cmake_path, "w", encoding="utf-8") as f:
            f.write(cmake)

        # 3. C++ Header
        cpp_h = self.generate_cpp_header(safe_name)
        cpp_h_path = os.path.join(output_dir, "src", f"{safe_name}_plugin.h")
        with open(cpp_h_path, "w", encoding="utf-8") as f:
            f.write(cpp_h)

        # 4. C++ Source
        cpp_src = self.generate_cpp_source(safe_name)
        cpp_src_path = os.path.join(output_dir, "src", f"{safe_name}_plugin.cpp")
        with open(cpp_src_path, "w", encoding="utf-8") as f:
            f.write(cpp_src)

        return {
            "cmake": cmake_path,
            "c_header": c_header_path,
            "cpp_header": cpp_h_path,
            "cpp_source": cpp_src_path,
        }
