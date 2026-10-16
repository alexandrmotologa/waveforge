/* WaveForge Web Studio Interactive JavaScript Engine */

(function () {
  let currentPatch = {
    name: "Acid 303 Bass",
    author: "WaveForge",
    sample_rate: 44100,
    block_size: 128,
    nodes: [],
    connections: []
  };

  let nodeCatalog = [];
  let currentAudio = null;
  let activeNote = "C3";
  let connectingState = null; // { fromNode, fromPin, x1, y1 }

  // Undo / Redo History Stacks
  let historyStack = [];
  let redoStack = [];

  function pushHistoryState() {
    historyStack.push(JSON.parse(JSON.stringify(currentPatch)));
    if (historyStack.length > 50) historyStack.shift();
    redoStack = [];
    updateUndoRedoButtons();
  }

  function undo() {
    if (historyStack.length === 0) return;
    redoStack.push(JSON.parse(JSON.stringify(currentPatch)));
    currentPatch = historyStack.pop();
    renderGraph();
    updateUndoRedoButtons();
  }

  function redo() {
    if (redoStack.length === 0) return;
    historyStack.push(JSON.parse(JSON.stringify(currentPatch)));
    currentPatch = redoStack.pop();
    renderGraph();
    updateUndoRedoButtons();
  }

  function updateUndoRedoButtons() {
    const uBtn = document.getElementById("btn-undo");
    const rBtn = document.getElementById("btn-redo");
    if (uBtn) {
      uBtn.style.opacity = historyStack.length > 0 ? "1.0" : "0.4";
      uBtn.disabled = historyStack.length === 0;
    }
    if (rBtn) {
      rBtn.style.opacity = redoStack.length > 0 ? "1.0" : "0.4";
      rBtn.disabled = redoStack.length === 0;
    }
  }

  // Canvas elements
  const canvasContainer = document.getElementById("canvas-container");
  const cablesSvg = document.getElementById("cables-svg");
  const nodesLayer = document.getElementById("nodes-layer");

  // Visualizer elements
  const oscCanvas = document.getElementById("oscilloscope-canvas");
  const oscCtx = oscCanvas.getContext("2d");
  const specCanvas = document.getElementById("spectrum-canvas");
  const specCtx = specCanvas.getContext("2d");

  // Stats elements
  const statRt = document.getElementById("stat-rt");
  const statPeak = document.getElementById("stat-peak");
  const statRms = document.getElementById("stat-rms");

  // --- Initial Setup ---
  async function init() {
    await loadNodeCatalog();
    await loadPreset("acid_303");
    setupPianoKeyboard();
    setupEvents();
    renderCables();
    drawIdleWaveform();
    updateUndoRedoButtons();
  }

  // --- Catalog & Presets ---
  async function loadNodeCatalog() {
    try {
      const res = await fetch("/api/nodes");
      const data = await res.json();
      nodeCatalog = data.nodes;
      populateAddNodeModal();
    } catch (err) {
      console.error("Failed to load node catalog:", err);
    }
  }

  async function loadPreset(presetId) {
    try {
      pushHistoryState();
      const res = await fetch(`/api/preset/${presetId}`);
      currentPatch = await res.json();
      renderGraph();
    } catch (err) {
      console.error("Failed to load preset:", err);
    }
  }

  // --- Graph UI Rendering ---
  function renderGraph() {
    nodesLayer.innerHTML = "";

    currentPatch.nodes.forEach(node => {
      const card = createNodeElement(node);
      nodesLayer.appendChild(card);
    });

    renderCables();
  }

  function createNodeElement(node) {
    const meta = nodeCatalog.find(m => m.type_id === node.type_id) || {
      display_name: node.type_id,
      inputs: [],
      outputs: []
    };

    const card = document.createElement("div");
    card.className = "node-card";
    card.id = `node-${node.id}`;
    card.style.left = `${node.x || 100}px`;
    card.style.top = `${node.y || 100}px`;

    // Header
    const header = document.createElement("div");
    header.className = "node-header";
    header.innerHTML = `
      <span class="node-title">${meta.display_name}</span>
      <button class="node-close-btn" title="Remove Node">&times;</button>
    `;

    header.querySelector(".node-close-btn").addEventListener("click", (e) => {
      e.stopPropagation();
      pushHistoryState();
      removeNode(node.id);
    });

    card.appendChild(header);

    // Body
    const body = document.createElement("div");
    body.className = "node-body";

    // Pins Row
    const pinsRow = document.createElement("div");
    pinsRow.className = "node-pins-row";

    // Inputs column
    const inCol = document.createElement("div");
    inCol.className = "pins-column inputs";
    meta.inputs.forEach(pin => {
      const isConnected = currentPatch.connections.some(c => c.to_node === node.id && c.to_pin === pin.name);
      const item = document.createElement("div");
      item.className = "pin-item";
      item.innerHTML = `
        <div class="pin-socket type-${pin.pin_type} ${isConnected ? 'connected' : ''}"
             data-node="${node.id}" data-pin="${pin.name}" data-dir="in"></div>
        <span>${pin.name}</span>
      `;
      inCol.appendChild(item);
    });

    // Outputs column
    const outCol = document.createElement("div");
    outCol.className = "pins-column outputs";
    meta.outputs.forEach(pin => {
      const isConnected = currentPatch.connections.some(c => c.from_node === node.id && c.from_pin === pin.name);
      const item = document.createElement("div");
      item.className = "pin-item";
      item.innerHTML = `
        <span>${pin.name}</span>
        <div class="pin-socket type-${pin.pin_type} ${isConnected ? 'connected' : ''}"
             data-node="${node.id}" data-pin="${pin.name}" data-dir="out"></div>
      `;
      outCol.appendChild(item);
    });

    pinsRow.appendChild(inCol);
    pinsRow.appendChild(outCol);
    body.appendChild(pinsRow);

    // Parameters
    const paramsDiv = document.createElement("div");
    paramsDiv.className = "node-params";
    for (const [paramKey, paramVal] of Object.entries(node.params || {})) {
      const pRow = document.createElement("div");
      pRow.className = "node-param";

      if (typeof paramVal === "boolean") {
        pRow.innerHTML = `
          <label style="font-size:10px; color:var(--text-dim); display:flex; align-items:center; gap:4px;">
            <input type="checkbox" ${paramVal ? "checked" : ""} data-param="${paramKey}">
            ${paramKey}
          </label>
        `;
        pRow.querySelector("input").addEventListener("change", (e) => {
          pushHistoryState();
          node.params[paramKey] = e.target.checked;
        });
      } else if (typeof paramVal === "string") {
        pRow.innerHTML = `
          <div class="param-header"><span>${paramKey}</span></div>
          <input type="text" class="param-select" value="${paramVal}" data-param="${paramKey}">
        `;
        pRow.querySelector("input").addEventListener("change", (e) => {
          pushHistoryState();
          node.params[paramKey] = e.target.value;
        });
      } else {
        // Numeric slider
        const minVal = paramVal > 10 ? 10 : 0.0;
        const maxVal = paramVal > 10 ? 10000 : (paramVal > 1.0 ? 10.0 : 1.0);
        const step = paramVal > 10 ? 1 : 0.01;

        pRow.innerHTML = `
          <div class="param-header">
            <span>${paramKey}</span>
            <span class="param-val-text">${Number(paramVal).toFixed(2)}</span>
          </div>
          <input type="range" class="param-input" min="${minVal}" max="${maxVal}" step="${step}" value="${paramVal}">
        `;

        const slider = pRow.querySelector("input");
        const valText = pRow.querySelector(".param-val-text");
        slider.addEventListener("input", (e) => {
          const v = parseFloat(e.target.value);
          node.params[paramKey] = v;
          valText.textContent = v.toFixed(2);
        });
        slider.addEventListener("change", () => {
          pushHistoryState();
        });
      }

      paramsDiv.appendChild(pRow);
    }
    body.appendChild(paramsDiv);
    card.appendChild(body);

    // Draggable card functionality
    makeDraggable(card, node);

    return card;
  }

  function makeDraggable(card, node) {
    let isDragging = false;
    let startX = 0, startY = 0;
    let initialX = 0, initialY = 0;

    const onMouseDown = (e) => {
      if (e.target.closest(".pin-socket") || e.target.closest("input") || e.target.closest("button")) {
        return;
      }
      isDragging = true;
      startX = e.clientX;
      startY = e.clientY;
      initialX = card.offsetLeft;
      initialY = card.offsetTop;
      card.classList.add("selected");
      document.addEventListener("mousemove", onMouseMove);
      document.addEventListener("mouseup", onMouseUp);
    };

    const onMouseMove = (e) => {
      if (!isDragging) return;
      const dx = e.clientX - startX;
      const dy = e.clientY - startY;
      const newX = Math.max(0, initialX + dx);
      const newY = Math.max(0, initialY + dy);
      card.style.left = `${newX}px`;
      card.style.top = `${newY}px`;
      node.x = newX;
      node.y = newY;
      renderCables();
    };

    const onMouseUp = () => {
      if (isDragging) {
        isDragging = false;
        card.classList.remove("selected");
        document.removeEventListener("mousemove", onMouseMove);
        document.removeEventListener("mouseup", onMouseUp);
        if (Math.abs(card.offsetLeft - initialX) > 2 || Math.abs(card.offsetTop - initialY) > 2) {
          pushHistoryState();
        }
      }
    };

    card.addEventListener("mousedown", onMouseDown);
  }

  // --- Patch Cable SVG Rendering ---
  function renderCables() {
    cablesSvg.innerHTML = "";

    currentPatch.connections.forEach((conn, index) => {
      const srcEl = document.querySelector(`.pin-socket[data-node="${conn.from_node}"][data-pin="${conn.from_pin}"][data-dir="out"]`);
      const tgtEl = document.querySelector(`.pin-socket[data-node="${conn.to_node}"][data-pin="${conn.to_pin}"][data-dir="in"]`);

      if (!srcEl || !tgtEl) return;

      const p1 = getSocketCenter(srcEl);
      const p2 = getSocketCenter(tgtEl);

      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      const d = createBezierPath(p1.x, p1.y, p2.x, p2.y);
      path.setAttribute("d", d);
      path.setAttribute("stroke", srcEl.classList.contains("type-control") ? "#f59e0b" : "#10b981");
      path.setAttribute("stroke-width", "3");
      path.setAttribute("fill", "none");
      path.setAttribute("stroke-linecap", "round");
      path.style.cursor = "pointer";
      path.style.filter = "drop-shadow(0 0 4px rgba(16, 185, 129, 0.4))";

      // Disconnect on cable click
      path.addEventListener("click", () => {
        pushHistoryState();
        currentPatch.connections.splice(index, 1);
        renderGraph();
      });

      cablesSvg.appendChild(path);
    });
  }

  function getSocketCenter(el) {
    const rect = el.getBoundingClientRect();
    const containerRect = canvasContainer.getBoundingClientRect();
    return {
      x: rect.left - containerRect.left + canvasContainer.scrollLeft + rect.width / 2,
      y: rect.top - containerRect.top + canvasContainer.scrollTop + rect.height / 2
    };
  }

  function createBezierPath(x1, y1, x2, y2) {
    const dx = Math.abs(x2 - x1) * 0.5;
    const dy = Math.abs(y2 - y1) * 0.2;
    const cx1 = x1 + Math.max(50, dx);
    const cy1 = y1 + dy;
    const cx2 = x2 - Math.max(50, dx);
    const cy2 = y2 - dy;
    return `M ${x1} ${y1} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${x2} ${y2}`;
  }

  // --- Node & Cable Manipulation ---
  function removeNode(nodeId) {
    currentPatch.nodes = currentPatch.nodes.filter(n => n.id !== nodeId);
    currentPatch.connections = currentPatch.connections.filter(c => c.from_node !== nodeId && c.to_node !== nodeId);
    renderGraph();
  }

  function addNode(typeId) {
    pushHistoryState();
    const meta = nodeCatalog.find(m => m.type_id === typeId);
    if (!meta) return;

    const count = currentPatch.nodes.filter(n => n.type_id === typeId).length + 1;
    const newNode = {
      id: `${typeId}_${count}`,
      type_id: typeId,
      x: canvasContainer.scrollLeft + 150 + count * 20,
      y: canvasContainer.scrollTop + 120 + count * 20,
      params: { ...meta.default_params }
    };

    currentPatch.nodes.push(newNode);
    renderGraph();
  }

  // Socket connection handling
  document.addEventListener("mousedown", (e) => {
    const socket = e.target.closest(".pin-socket");
    if (!socket) return;

    const node = socket.getAttribute("data-node");
    const pin = socket.getAttribute("data-pin");
    const dir = socket.getAttribute("data-dir");

    if (dir === "out") {
      const p = getSocketCenter(socket);
      connectingState = {
        fromNode: node,
        fromPin: pin,
        x1: p.x,
        y1: p.y
      };

      const tempPath = document.createElementNS("http://www.w3.org/2000/svg", "path");
      tempPath.id = "temp-cable";
      tempPath.setAttribute("stroke", "#38bdf8");
      tempPath.setAttribute("stroke-width", "2.5");
      tempPath.setAttribute("stroke-dasharray", "4 4");
      tempPath.setAttribute("fill", "none");
      cablesSvg.appendChild(tempPath);

      const onMouseMoveCable = (ev) => {
        if (!connectingState) return;
        const containerRect = canvasContainer.getBoundingClientRect();
        const curX = ev.clientX - containerRect.left + canvasContainer.scrollLeft;
        const curY = ev.clientY - containerRect.top + canvasContainer.scrollTop;
        tempPath.setAttribute("d", createBezierPath(connectingState.x1, connectingState.y1, curX, curY));
      };

      const onMouseUpCable = (ev) => {
        document.removeEventListener("mousemove", onMouseMoveCable);
        document.removeEventListener("mouseup", onMouseUpCable);
        const temp = document.getElementById("temp-cable");
        if (temp) temp.remove();

        const targetSocket = ev.target.closest(".pin-socket");
        if (targetSocket && targetSocket.getAttribute("data-dir") === "in") {
          const toNode = targetSocket.getAttribute("data-node");
          const toPin = targetSocket.getAttribute("data-pin");

          if (connectingState.fromNode !== toNode) {
            pushHistoryState();
            // Remove existing connection to target pin
            currentPatch.connections = currentPatch.connections.filter(c => !(c.to_node === toNode && c.to_pin === toPin));
            currentPatch.connections.push({
              from_node: connectingState.fromNode,
              from_pin: connectingState.fromPin,
              to_node: toNode,
              to_pin: toPin
            });
            renderGraph();
          }
        }
        connectingState = null;
      };

      document.addEventListener("mousemove", onMouseMoveCable);
      document.addEventListener("mouseup", onMouseUpCable);
    }
  });

  // --- Sound Playback & Visualizer ---
  async function playSound(note = activeNote) {
    const playBtn = document.getElementById("btn-play");
    playBtn.classList.add("playing");

    try {
      const res = await fetch("/api/render", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          patch: currentPatch,
          note: note,
          duration: 2.0,
          velocity: 0.85
        })
      });

      if (!res.ok) throw new Error("Render error");
      const data = await res.json();

      updateVisualizers(data);
      playAudioBuffer(data.audio_base64);
    } catch (err) {
      console.error("Playback error:", err);
    } finally {
      setTimeout(() => playBtn.classList.remove("playing"), 300);
    }
  }

  async function playPolyphonicSound() {
    const polyBtn = document.getElementById("btn-render-poly");
    polyBtn.classList.add("playing");

    try {
      const res = await fetch("/api/render-poly", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          patch: currentPatch,
          note: "C3",
          duration: 2.5,
          velocity: 0.85
        })
      });

      if (!res.ok) throw new Error("Polyphonic render error");
      const data = await res.json();

      updateVisualizers(data);
      playAudioBuffer(data.audio_base64);
    } catch (err) {
      console.error("Polyphonic playback error:", err);
    } finally {
      setTimeout(() => polyBtn.classList.remove("playing"), 300);
    }
  }

  function playAudioBuffer(base64Wav) {
    if (currentAudio) {
      currentAudio.pause();
      currentAudio = null;
    }

    const audioUrl = "data:audio/wav;base64," + base64Wav;
    currentAudio = new Audio(audioUrl);
    currentAudio.play().catch(e => console.log("Audio autoplay restricted:", e));
  }

  function updateVisualizers(data) {
    // Stats
    if (data.realtime_factor) statRt.textContent = `${data.realtime_factor.toFixed(1)}x`;
    const peakDb = 20.0 * Math.log10(Math.max(data.peak || 1e-4, 1e-4));
    const rmsDb = 20.0 * Math.log10(Math.max(data.rms || 1e-4, 1e-4));
    statPeak.textContent = `${peakDb.toFixed(1)} dB`;
    statRms.textContent = `${rmsDb.toFixed(1)} dB`;

    // Oscilloscope waveform
    if (data.waveform) drawWaveform(data.waveform);

    // FFT Spectrum
    if (data.spectrum) drawSpectrum(data.spectrum);
  }

  function drawIdleWaveform() {
    const w = oscCanvas.width;
    const h = oscCanvas.height;
    oscCtx.fillStyle = "#11141e";
    oscCtx.fillRect(0, 0, w, h);
    oscCtx.strokeStyle = "#334155";
    oscCtx.lineWidth = 1;
    oscCtx.beginPath();
    oscCtx.moveTo(0, h / 2);
    oscCtx.lineTo(w, h / 2);
    oscCtx.stroke();
  }

  function drawWaveform(waveform) {
    const w = oscCanvas.width;
    const h = oscCanvas.height;
    oscCtx.fillStyle = "#11141e";
    oscCtx.fillRect(0, 0, w, h);

    // Center gridline
    oscCtx.strokeStyle = "rgba(51, 65, 85, 0.4)";
    oscCtx.beginPath();
    oscCtx.moveTo(0, h / 2);
    oscCtx.lineTo(w, h / 2);
    oscCtx.stroke();

    // Waveform curve
    oscCtx.strokeStyle = "#10b981";
    oscCtx.lineWidth = 2;
    oscCtx.beginPath();

    const sliceW = w / waveform.length;
    let x = 0;

    for (let i = 0; i < waveform.length; i++) {
      const v = waveform[i];
      const y = (0.5 - v * 0.45) * h;

      if (i === 0) oscCtx.moveTo(x, y);
      else oscCtx.lineTo(x, y);

      x += sliceW;
    }
    oscCtx.stroke();
  }

  function drawSpectrum(spectrum) {
    const w = specCanvas.width;
    const h = specCanvas.height;
    specCtx.fillStyle = "#11141e";
    specCtx.fillRect(0, 0, w, h);

    const barWidth = Math.max(1, w / spectrum.length);

    for (let i = 0; i < spectrum.length; i++) {
      const db = spectrum[i]; // -80 to +10 dB
      const normalized = Math.max(0, Math.min(1, (db + 80.0) / 90.0));
      const barH = normalized * h;

      const grad = specCtx.createLinearGradient(0, h, 0, 0);
      grad.addColorStop(0, "#06b6d4");
      grad.addColorStop(1, "rgba(6, 182, 212, 0.1)");

      specCtx.fillStyle = grad;
      specCtx.fillRect(i * barWidth, h - barH, barWidth - 1, barH);
    }
  }

  // --- Virtual Keyboard ---
  function setupPianoKeyboard() {
    const keyboard = document.getElementById("piano-keyboard");
    keyboard.innerHTML = "";

    const notes = [
      { name: "C2", isBlack: false }, { name: "C#2", isBlack: true },
      { name: "D2", isBlack: false }, { name: "D#2", isBlack: true },
      { name: "E2", isBlack: false },
      { name: "F2", isBlack: false }, { name: "F#2", isBlack: true },
      { name: "G2", isBlack: false }, { name: "G#2", isBlack: true },
      { name: "A2", isBlack: false }, { name: "A#2", isBlack: true },
      { name: "B2", isBlack: false },
      { name: "C3", isBlack: false }, { name: "C#3", isBlack: true },
      { name: "D3", isBlack: false }, { name: "D#3", isBlack: true },
      { name: "E3", isBlack: false },
      { name: "F3", isBlack: false }, { name: "F#3", isBlack: true },
      { name: "G3", isBlack: false }, { name: "G#3", isBlack: true },
      { name: "A3", isBlack: false }, { name: "A#3", isBlack: true },
      { name: "B3", isBlack: false },
      { name: "C4", isBlack: false },
    ];

    let whiteCount = 0;
    notes.forEach(note => {
      const key = document.createElement("div");
      key.dataset.note = note.name;

      if (!note.isBlack) {
        key.className = "key-white";
        key.textContent = note.name;
        whiteCount++;
      } else {
        key.className = "key-black";
        key.textContent = note.name;
        key.style.left = `${(whiteCount * 28) - 10}px`;
      }

      key.addEventListener("mousedown", () => {
        key.classList.add("active");
        activeNote = note.name;
        playSound(note.name);
      });

      key.addEventListener("mouseup", () => key.classList.remove("active"));
      key.addEventListener("mouseleave", () => key.classList.remove("active"));

      keyboard.appendChild(key);
    });
  }

  // --- Add Node Modal ---
  function populateAddNodeModal() {
    const grid = document.getElementById("node-catalog-grid");
    grid.innerHTML = "";

    nodeCatalog.forEach(item => {
      const card = document.createElement("div");
      card.className = "catalog-item";
      card.innerHTML = `
        <div class="catalog-item-title">${item.display_name}</div>
        <div class="catalog-item-desc">${item.description}</div>
      `;
      card.addEventListener("click", () => {
        addNode(item.type_id);
        document.getElementById("modal-add-node").classList.add("hidden");
      });
      grid.appendChild(card);
    });
  }

  // --- Export C Header ---
  async function openExportCModal() {
    try {
      const res = await fetch("/api/export-c", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ patch: currentPatch })
      });
      const data = await res.json();
      document.querySelector("#c-code-view code").textContent = data.c_code;
      document.getElementById("modal-export-c").classList.remove("hidden");
    } catch (err) {
      console.error("Export C failed:", err);
    }
  }

  // --- Export HTML5 Single-File Player ---
  async function downloadHtmlPlayer() {
    try {
      const res = await fetch("/api/export-html", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ patch: currentPatch })
      });
      const data = await res.json();
      const blob = new Blob([data.html], { type: "text/html" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `${currentPatch.name.toLowerCase().replace(/[^a-z0-9]/g, "_")}_player.html`;
      a.click();
    } catch (err) {
      console.error("Export HTML player failed:", err);
    }
  }

  // --- Export VST/CLAP Plugin Modal ---
  async function openExportPluginModal() {
    try {
      const res = await fetch("/api/export-plugin", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ patch: currentPatch })
      });
      const data = await res.json();
      const preview = `// --- CMakeLists.txt ---\n${data.cmake}\n\n// --- WaveForgeSynth_plugin.h ---\n${data.cpp_header}\n\n// --- WaveForgeSynth_plugin.cpp ---\n${data.cpp_source}`;
      document.querySelector("#plugin-code-view code").textContent = preview;
      document.getElementById("modal-export-plugin").classList.remove("hidden");
    } catch (err) {
      console.error("Export Plugin failed:", err);
    }
  }

  // --- Event Listeners ---
  function setupEvents() {
    // Undo / Redo
    const btnUndo = document.getElementById("btn-undo");
    const btnRedo = document.getElementById("btn-redo");
    if (btnUndo) btnUndo.addEventListener("click", undo);
    if (btnRedo) btnRedo.addEventListener("click", redo);

    // Preset dropdown
    document.getElementById("preset-select").addEventListener("change", (e) => {
      loadPreset(e.target.value);
    });

    // Top action buttons
    document.getElementById("btn-play").addEventListener("click", () => playSound());
    document.getElementById("btn-render-poly").addEventListener("click", () => playPolyphonicSound());
    document.getElementById("btn-add-node").addEventListener("click", () => {
      document.getElementById("modal-add-node").classList.remove("hidden");
    });
    document.getElementById("btn-export-c").addEventListener("click", openExportCModal);
    document.getElementById("btn-export-html").addEventListener("click", downloadHtmlPlayer);
    document.getElementById("btn-export-plugin").addEventListener("click", openExportPluginModal);

    // Download WAV button
    document.getElementById("btn-download-wav").addEventListener("click", async () => {
      const res = await fetch("/api/render", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ patch: currentPatch, note: activeNote, duration: 3.0 })
      });
      const data = await res.json();
      const a = document.createElement("a");
      a.href = "data:audio/wav;base64," + data.audio_base64;
      a.download = `${currentPatch.name.toLowerCase().replace(/[^a-z0-9]/g, "_")}.wav`;
      a.click();
    });

    // Close modals
    document.getElementById("btn-close-node-modal").addEventListener("click", () => {
      document.getElementById("modal-add-node").classList.add("hidden");
    });
    document.getElementById("btn-close-c-modal").addEventListener("click", () => {
      document.getElementById("modal-export-c").classList.add("hidden");
    });
    const closePluginModal = document.getElementById("btn-close-plugin-modal");
    if (closePluginModal) {
      closePluginModal.addEventListener("click", () => {
        document.getElementById("modal-export-plugin").classList.add("hidden");
      });
    }

    // Copy C code
    document.getElementById("btn-copy-c").addEventListener("click", () => {
      const code = document.querySelector("#c-code-view code").textContent;
      navigator.clipboard.writeText(code).then(() => {
        alert("C Header copied to clipboard!");
      });
    });

    // Download C Header
    document.getElementById("btn-download-c").addEventListener("click", () => {
      const code = document.querySelector("#c-code-view code").textContent;
      const blob = new Blob([code], { type: "text/plain" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "waveforge_synth.h";
      a.click();
    });

    // Copy Plugin code
    const copyPluginBtn = document.getElementById("btn-copy-plugin");
    if (copyPluginBtn) {
      copyPluginBtn.addEventListener("click", () => {
        const code = document.querySelector("#plugin-code-view code").textContent;
        navigator.clipboard.writeText(code).then(() => {
          alert("Plugin code copied to clipboard!");
        });
      });
    }

    // Keyboard shortcuts: Space for play, Ctrl+Z for undo, Ctrl+Y for redo
    window.addEventListener("keydown", (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "z") {
        if (e.shiftKey) {
          e.preventDefault();
          redo();
        } else {
          e.preventDefault();
          undo();
        }
      } else if ((e.ctrlKey || e.metaKey) && e.key === "y") {
        e.preventDefault();
        redo();
      } else if (e.code === "Space" && e.target.tagName !== "INPUT") {
        e.preventDefault();
        playSound();
      }
    });
  }

  // Boot on DOM ready
  window.addEventListener("DOMContentLoaded", init);
})();
