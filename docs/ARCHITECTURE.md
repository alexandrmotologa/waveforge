# WaveForge Architecture

WaveForge is a modular audio Digital Signal Processing (DSP) engine, visual node synthesizer, and zero-dependency C/WebAssembly code generator.

```
                           +----------------------+
                           |   AudioConfig (I/O)  |
                           +----------+-----------+
                                      |
                                      v
+------------------+       +----------+-----------+       +-------------------+
|  PolyBLEP Osc    | ----> |   Biquad Filters     | ----> |   Master Limiter  |
|  (Saw, Sq, Tri)  |       |   (RBJ / SVF)        |       |   (OutputNode)    |
+------------------+       +----------+-----------+       +---------+---------+
         ^                            ^                             |
         |                            |                             v
+--------+---------+       +----------+-----------+       +---------+---------+
|  ADSR Envelopes  |       |   Effects Engine     |       |   Audio Output    |
|  (RC analog exp) |       | (Delay, Sat, Reverb) |       |  (WAV / Speaker)  |
+------------------+       +----------------------+       +-------------------+
```

## System Layers

### 1. DSP Mathematical Core (`src/waveforge/core`)
- **Oscillators (`oscillators.py`)**: PolyBLEP residual algorithm for step discontinuity correction. Generates band-limited Saw, Square (variable duty pulse width), and Triangle waveforms with suppression of Nyquist harmonic folding.
- **Filters (`filters.py`)**: Robert Bristow-Johnson Audio EQ Cookbook biquad filters in Direct Form II Transposed (DF2T) structure for low round-off noise and float precision stability. Chamberlin 2-pole State Variable Filter (SVF) with 2x internal oversampling for simultaneous lowpass, highpass, bandpass, and notch outputs.
- **Envelopes (`envelopes.py`)**: Exponential attack, decay, sustain, and release modeled after analog capacitor RC charging dynamics.
- **Modulation (`modulation.py`)**: Cyclic LFO with multi-waveform shapes, sample and hold clock latches, and peak envelope followers with attack and release ballistics.
- **Effects (`effects.py`)**: Fractional stereo ping-pong delay with Hermite interpolation and high-frequency damping; waveshaping saturation (tanh, cubic, diode, wavefolder); Schroeder-Moorer digital reverberator (8 parallel comb filters, 4 series allpass diffusors).

### 2. Graph and DAG Execution Engine (`src/waveforge/graph`)
- **Nodes (`node.py`)**: Processing blocks with typed pin sockets (Audio-rate, Control Voltage, Parameter).
- **Patch Routing (`patch.py`)**: Directed graph representation supporting connection validation, cyclic feedback tracking, and serialization to JSON schemas.
- **DAG Evaluator (`engine.py`)**: Topological sorting using Kahn's algorithm. Evaluates audio blocks through preallocated buffers without dynamic memory allocations in the inner loop.

### 3. Code Generation (`src/waveforge/codegen`)
- **C Generator (`c_generator.py`)**: Transpiles any active patch graph into a standalone, single-file C99 header (`waveforge_synth.h`).
- **Zero External Dependencies**: Uses standard C math library (`<math.h>`). Embeddable directly into games, microcontrollers, VST plugins, or WebAssembly runners.
- **Compiler Driver (`wasm_builder.py`)**: Invokes clang or gcc to compile and verify native binaries directly.

### 4. Interactive Web Studio (`src/waveforge/studio`)
- **FastAPI Backend**: Serves modular synthesis APIs, computes audio renders, calculates real-time FFT spectrum analysis and waveform data, and provides standalone C code downloads.
- **Client Frontend**: SVG-based modular patch rack with interactive bezier cable patching, real-time oscilloscope, spectrum analyzer, and playable virtual keyboard.
