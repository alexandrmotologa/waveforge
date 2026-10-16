"""FastAPI Web Studio backend for visual modular node synthesis."""

from __future__ import annotations
import base64
import os
import time
import numpy as np
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from waveforge.core.config import PatchSchema
from waveforge.graph.patch import NodeGraph
from waveforge.graph.engine import AudioEngine
from waveforge.graph.presets import PRESET_CATALOG
from waveforge.graph.node import NODE_REGISTRY
from waveforge.codegen.c_generator import CCodeGenerator
from waveforge.audio.wav_io import get_wav_bytes
from waveforge.audio.midi import note_name_to_midi

app = FastAPI(
    title="WaveForge Studio API",
    description="Modular audio DSP engine and visual node synthesizer API",
    version="0.1.0",
)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class RenderRequest(BaseModel):
    patch: PatchSchema
    note: str = "C3"
    duration: float = 2.0
    velocity: float = 0.85


class ExportCRequest(BaseModel):
    patch: PatchSchema
    guard: str = "WAVEFORGE_SYNTH_H"


@app.get("/", response_class=HTMLResponse)
async def get_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>WaveForge Web Studio: static/index.html not found</h1>")


@app.get("/api/nodes")
async def get_nodes_catalog():
    """Return all available DSP node types and metadata."""
    nodes = []
    for type_id, cls in sorted(NODE_REGISTRY.items()):
        meta = cls.get_metadata()
        nodes.append(meta.model_dump())
    return JSONResponse(content={"nodes": nodes})


@app.get("/api/presets")
async def get_presets():
    """Return catalog of available built-in modular patches."""
    presets = []
    for pid, factory in PRESET_CATALOG.items():
        g = factory()
        presets.append({
            "id": pid,
            "name": g.name,
            "patch": g.to_dict(),
        })
    return JSONResponse(content={"presets": presets})


@app.get("/api/preset/{name}")
async def get_preset(name: str):
    """Retrieve full patch schema for a preset."""
    if name not in PRESET_CATALOG:
        raise HTTPException(status_code=404, detail=f"Preset '{name}' not found")
    g = PRESET_CATALOG[name]()
    return JSONResponse(content=g.to_dict())


@app.post("/api/render")
async def render_patch(req: RenderRequest):
    """Render a modular patch into audio WAV and frequency analysis vectors."""
    try:
        graph = NodeGraph.from_schema(req.patch)
        midi_note = int(req.note) if req.note.isdigit() else note_name_to_midi(req.note)

        engine = AudioEngine(graph)
        start_time = time.perf_counter()
        left, right = engine.render(
            duration_sec=req.duration,
            midi_note=midi_note,
            velocity=req.velocity,
        )
        elapsed = time.perf_counter() - start_time

        wav_bytes = get_wav_bytes(left, right, sample_rate=graph.sample_rate, bit_depth=16)
        b64_audio = base64.b64encode(wav_bytes).decode("ascii")

        # Downsample waveform for visual oscilloscope (512 points)
        step = max(1, len(left) // 512)
        waveform_vis = left[::step][:512].tolist()

        # FFT Spectrum Analysis (first 1024 bins)
        fft_len = 2048
        windowed = left[:fft_len] * np.hanning(min(len(left), fft_len))
        fft_mag = np.abs(np.fft.rfft(windowed, n=fft_len))
        # Convert to dB
        fft_db = 20.0 * np.log10(np.maximum(fft_mag, 1e-5))
        fft_db = np.clip(fft_db, -80.0, 10.0)
        spectrum_vis = fft_db[:256].tolist()

        peak = float(np.max(np.abs(left)))
        rms = float(np.sqrt(np.mean(left ** 2)))

        return JSONResponse(content={
            "audio_base64": b64_audio,
            "elapsed_sec": elapsed,
            "realtime_factor": req.duration / elapsed if elapsed > 0 else 0,
            "peak": peak,
            "rms": rms,
            "waveform": waveform_vis,
            "spectrum": spectrum_vis,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/export-c")
async def export_c_code(req: ExportCRequest):
    """Generate standalone C99 header source code from patch."""
    try:
        graph = NodeGraph.from_schema(req.patch)
        gen = CCodeGenerator(graph)
        c_code = gen.generate_header(guard_name=req.guard)
        return JSONResponse(content={"c_code": c_code})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
