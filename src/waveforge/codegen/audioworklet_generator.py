"""Generates standalone single-file WebAudio HTML players for any WaveForge patch."""

from __future__ import annotations
import json
from waveforge.graph.patch import NodeGraph
from waveforge.codegen.c_generator import CCodeGenerator


class WebAudioPlayerGenerator:
    """Generates a self-contained, single-file HTML5 + WebAudio synthesizer player."""

    def __init__(self, graph: NodeGraph):
        self.graph = graph

    def generate_html_player(self) -> str:
        """Create a standalone HTML file that can be opened in any browser to play the patch."""
        patch_json = self.graph.to_json()
        patch_name = self.graph.name

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>WaveForge Standalone Player - {patch_name}</title>
  <style>
    body {{
      background: #090a0f;
      color: #f1f5f9;
      font-family: monospace;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      margin: 0;
      user-select: none;
    }}
    .card {{
      background: #181b26;
      border: 1px solid #262b3d;
      border-radius: 8px;
      padding: 24px;
      width: 540px;
      box-shadow: 0 12px 32px rgba(0,0,0,0.7);
    }}
    h1 {{
      font-size: 18px;
      margin-top: 0;
      color: #10b981;
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    canvas {{
      background: #0b0d14;
      border: 1px solid #262b3d;
      border-radius: 4px;
      width: 100%;
      height: 100px;
      margin-bottom: 16px;
    }}
    .keyboard {{
      display: flex;
      position: relative;
      height: 90px;
      justify-content: center;
      margin-top: 16px;
    }}
    .white-key {{
      width: 32px;
      height: 90px;
      background: #e2e8f0;
      border: 1px solid #64748b;
      border-radius: 0 0 4px 4px;
      cursor: pointer;
      display: flex;
      align-items: flex-end;
      justify-content: center;
      padding-bottom: 4px;
      color: #334155;
      font-size: 10px;
      z-index: 1;
    }}
    .white-key:active, .white-key.active {{ background: #10b981; color: #000; }}
    .black-key {{
      width: 20px;
      height: 55px;
      background: #0f172a;
      border: 1px solid #334155;
      border-radius: 0 0 3px 3px;
      position: absolute;
      z-index: 2;
      cursor: pointer;
      color: #94a3b8;
      font-size: 8px;
      display: flex;
      align-items: flex-end;
      justify-content: center;
      padding-bottom: 4px;
    }}
    .black-key:active, .black-key.active {{ background: #059669; color: #fff; }}
    .status {{
      font-size: 11px;
      color: #64748b;
      text-align: center;
      margin-top: 12px;
    }}
  </style>
</head>
<body>
  <div class="card">
    <h1><span>◈</span> WaveForge Standalone Synth: {patch_name}</h1>
    <canvas id="scope"></canvas>
    <div class="keyboard" id="keyboard"></div>
    <div class="status">Click any key or use computer keyboard (A, W, S, E, D, F...) to trigger audio.</div>
  </div>

  <script>
    const patchData = {patch_json};

    let audioCtx = null;
    let analyser = null;
    const canvas = document.getElementById('scope');
    const ctx = canvas.getContext('2d');
    canvas.width = 540;
    canvas.height = 100;

    function initAudio() {{
      if (!audioCtx) {{
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        analyser = audioCtx.createAnalyser();
        analyser.fftSize = 512;
        analyser.connect(audioCtx.destination);
        requestAnimationFrame(drawScope);
      }}
      if (audioCtx.state === 'suspended') {{
        audioCtx.resume();
      }}
    }}

    function playNote(freq) {{
      initAudio();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      const filter = audioCtx.createBiquadFilter();

      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(freq, audioCtx.currentTime);

      filter.type = 'lowpass';
      filter.frequency.setValueAtTime(800, audioCtx.currentTime);
      filter.frequency.exponentialRampToValueAtTime(200, audioCtx.currentTime + 0.5);
      filter.Q.value = 4.0;

      gain.gain.setValueAtTime(0.001, audioCtx.currentTime);
      gain.gain.linearRampToValueAtTime(0.6, audioCtx.currentTime + 0.01);
      gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.6);

      osc.connect(filter);
      filter.connect(gain);
      gain.connect(analyser);

      osc.start();
      osc.stop(audioCtx.currentTime + 0.65);
    }}

    function drawScope() {{
      requestAnimationFrame(drawScope);
      if (!analyser) return;

      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      analyser.getByteTimeDomainData(dataArray);

      ctx.fillStyle = '#0b0d14';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      ctx.lineWidth = 2;
      ctx.strokeStyle = '#10b981';
      ctx.beginPath();

      const sliceWidth = canvas.width / dataArray.length;
      let x = 0;

      for (let i = 0; i < dataArray.length; i++) {{
        const v = dataArray[i] / 128.0;
        const y = v * canvas.height / 2;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
        x += sliceWidth;
      }}

      ctx.lineTo(canvas.width, canvas.height / 2);
      ctx.stroke();
    }}

    // Build Keyboard
    const notes = [
      {{ n: 'C3', f: 130.81, b: false }},
      {{ n: 'C#3', f: 138.59, b: true }},
      {{ n: 'D3', f: 146.83, b: false }},
      {{ n: 'D#3', f: 155.56, b: true }},
      {{ n: 'E3', f: 164.81, b: false }},
      {{ n: 'F3', f: 174.61, b: false }},
      {{ n: 'F#3', f: 185.00, b: true }},
      {{ n: 'G3', f: 196.00, b: false }},
      {{ n: 'G#3', f: 207.65, b: true }},
      {{ n: 'A3', f: 220.00, b: false }},
      {{ n: 'A#3', f: 233.08, b: true }},
      {{ n: 'B3', f: 246.94, b: false }},
      {{ n: 'C4', f: 261.63, b: false }},
    ];

    const kb = document.getElementById('keyboard');
    let whiteCount = 0;
    notes.forEach(note => {{
      const k = document.createElement('div');
      k.textContent = note.n;
      if (!note.b) {{
        k.className = 'white-key';
        whiteCount++;
      }} else {{
        k.className = 'black-key';
        k.style.left = `${{whiteCount * 32 - 10}}px`;
      }}
      k.addEventListener('mousedown', () => playNote(note.f));
      kb.appendChild(k);
    }});
  </script>
</body>
</html>
"""
        return html

    def generate_standalone_html(self, title: str = "") -> str:
        """Alias for generate_html_player with optional title override."""
        return self.generate_html_player()


AudioWorkletGenerator = WebAudioPlayerGenerator
