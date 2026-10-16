"""C99, WebAssembly, AudioWorklet, and VST3/CLAP standalone synthesizer code generation."""

from waveforge.codegen.c_generator import CCodeGenerator
from waveforge.codegen.wasm_builder import CCompilerDriver
from waveforge.codegen.audioworklet_generator import AudioWorkletGenerator
from waveforge.codegen.plugin_generator import PluginGenerator

__all__ = [
    "CCodeGenerator",
    "CCompilerDriver",
    "AudioWorkletGenerator",
    "PluginGenerator",
]
