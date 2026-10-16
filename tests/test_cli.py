"""Tests for Typer CLI commands."""

import os
from typer.testing import CliRunner
from waveforge.cli.main import app

runner = CliRunner(env={"COLUMNS": "180"})


def test_cli_list_nodes():
    res = runner.invoke(app, ["list-nodes"])
    assert res.exit_code == 0
    assert "oscillator" in res.stdout
    assert "biquad_filter" in res.stdout
    assert "adsr" in res.stdout


def test_cli_list_presets():
    res = runner.invoke(app, ["list-presets"])
    assert res.exit_code == 0
    assert "acid_303" in res.stdout
    assert "sub_bass" in res.stdout


def test_cli_info():
    res = runner.invoke(app, ["info", "acid_303"])
    assert res.exit_code == 0
    assert "Acid 303 Bass" in res.stdout
    assert "osc1" in res.stdout


def test_cli_render(tmp_path):
    out_wav = str(tmp_path / "cli_test_render.wav")
    res = runner.invoke(app, ["render", "sub_bass", "-o", out_wav, "-d", "0.2"])
    assert res.exit_code == 0
    assert os.path.exists(out_wav)
    assert os.path.getsize(out_wav) > 1000


def test_cli_export_c(tmp_path):
    out_h = str(tmp_path / "synth.h")
    res = runner.invoke(app, ["export-c", "acid_303", "-o", out_h])
    assert res.exit_code == 0
    assert os.path.exists(out_h)
    with open(out_h, "r") as f:
        content = f.read()
    assert "WaveForgeSynth" in content


def test_cli_benchmark():
    res = runner.invoke(app, ["benchmark", "sub_bass", "-s", "1.0"])
    assert res.exit_code == 0
    assert "Megasamples/sec" in res.stdout
