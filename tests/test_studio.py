"""Tests for WaveForge FastAPI Web Studio endpoints."""

import pytest
from fastapi.testclient import TestClient
from waveforge.studio.app import app
from waveforge.graph.presets import create_acid_303_patch

client = TestClient(app)


def test_studio_index():
    res = client.get("/")
    assert res.status_code == 200
    assert "WaveForge" in res.text


def test_studio_api_nodes():
    res = client.get("/api/nodes")
    assert res.status_code == 200
    data = res.json()
    assert "nodes" in data
    type_ids = [n["type_id"] for n in data["nodes"]]
    assert "oscillator" in type_ids
    assert "biquad_filter" in type_ids
    assert "sequencer" in type_ids
    assert "drum_kick" in type_ids


def test_studio_api_presets():
    res = client.get("/api/presets")
    assert res.status_code == 200
    data = res.json()
    assert "presets" in data
    p_ids = [p["id"] for p in data["presets"]]
    assert "acid_303" in p_ids
    assert "techno_acid_seq" in p_ids
    assert "tr808_groove" in p_ids


def test_studio_render():
    patch = create_acid_303_patch().to_dict()
    res = client.post("/api/render", json={
        "patch": patch,
        "note": "C3",
        "duration": 0.2,
        "velocity": 0.8,
    })
    assert res.status_code == 200
    data = res.json()
    assert "audio_base64" in data
    assert "waveform" in data
    assert "spectrum" in data
    assert len(data["waveform"]) > 0


def test_studio_render_poly():
    patch = create_acid_303_patch().to_dict()
    res = client.post("/api/render-poly", json={
        "patch": patch,
        "note": "C3",
        "duration": 0.2,
        "velocity": 0.8,
    })
    assert res.status_code == 200
    data = res.json()
    assert "audio_base64" in data
    assert "waveform" in data


def test_studio_export_c():
    patch = create_acid_303_patch().to_dict()
    res = client.post("/api/export-c", json={
        "patch": patch,
        "guard": "TEST_SYNTH_H",
    })
    assert res.status_code == 200
    data = res.json()
    assert "c_code" in data
    assert "TEST_SYNTH_H" in data["c_code"]


def test_studio_export_html():
    patch = create_acid_303_patch().to_dict()
    res = client.post("/api/export-html", json={
        "patch": patch,
    })
    assert res.status_code == 200
    data = res.json()
    assert "html" in data
    assert "AudioContext" in data["html"]


def test_studio_export_plugin():
    patch = create_acid_303_patch().to_dict()
    res = client.post("/api/export-plugin", json={
        "patch": patch,
    })
    assert res.status_code == 200
    data = res.json()
    assert "cmake" in data
    assert "cpp_header" in data
    assert "cpp_source" in data
