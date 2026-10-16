# C and WebAssembly Code Generation Specification

WaveForge includes an integrated transpiler that turns any modular node graph into a single, standalone C99 header file (`waveforge_synth.h`).

## Design Goals

1. **Zero External Dependencies**: Pure ISO C99 standard library only (`<math.h>`, `<stdint.h>`, `<stdlib.h>`, `<string.h>`).
2. **Deterministic Memory Footprint**: All node state structures, delay lines, and filter registers are preallocated within a single `WaveForgeSynth` struct.
3. **Embeddable Anywhere**: Can be dropped into C/C++ games, VST/CLAP audio plugins, embedded platforms (Bela, Daisy Seed, Teensy, ESP32), or compiled directly to WebAssembly (`.wasm`).

## API Contract

```c
#include "waveforge_synth.h"

// 1. Initialize instance with sampling rate
WaveForgeSynth synth;
waveforge_synth_init(&synth, 44100.0f);

// 2. Note triggering
waveforge_synth_note_on(&synth, 60, 0.9f); // Note on: Middle C, 0.9 velocity
// ...
waveforge_synth_note_off(&synth);          // Note off

// 3. Audio buffer processing
float out_left[128];
float out_right[128];
waveforge_synth_process(&synth, out_left, out_right, 128);
```

## Compilation

### Native Binary (clang / gcc)
```bash
clang -O3 -DWAVEFORGE_STANDALONE waveforge_synth.h -o synth_runner.exe -lm
./synth_runner.exe
```

### WebAssembly Compilation (clang)
```bash
clang --target=wasm32 -O3 -nostdlib -Wl,--no-entry -Wl,--export-all waveforge_synth.c -o waveforge_synth.wasm
```
