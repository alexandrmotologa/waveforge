"""WaveForge Typer CLI: Render audio, export C code, benchmark DSP, and launch Web Studio."""

from __future__ import annotations
import os
import time
import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from waveforge.graph.patch import NodeGraph
from waveforge.graph.engine import AudioEngine
from waveforge.graph.presets import PRESET_CATALOG
from waveforge.graph.node import NODE_REGISTRY
from waveforge.codegen.c_generator import CCodeGenerator
from waveforge.codegen.wasm_builder import CCompilerDriver
from waveforge.audio.wav_io import write_wav
from waveforge.audio.midi import note_name_to_midi, midi_to_note_name
from waveforge.audio.player import AudioPlayer

app = typer.Typer(
    name="waveforge",
    help="WaveForge: Modular audio DSP engine, visual node synthesizer, and C/Wasm code generator.",
    add_completion=False,
)
console = Console()


def _resolve_graph(patch_or_preset: Optional[str]) -> NodeGraph:
    """Load graph from file or preset name."""
    if not patch_or_preset:
        return PRESET_CATALOG["acid_303"]()

    if os.path.exists(patch_or_preset):
        return NodeGraph.load(patch_or_preset)

    if patch_or_preset.lower() in PRESET_CATALOG:
        return PRESET_CATALOG[patch_or_preset.lower()]()

    available = list(PRESET_CATALOG.keys())
    raise typer.BadParameter(
        f"'{patch_or_preset}' is neither an existing file nor a valid preset. Available presets: {available}"
    )


@app.command("render")
def render_command(
    patch: Optional[str] = typer.Argument(None, help="Path to patch JSON or preset name (e.g. acid_303, sub_bass)"),
    out: str = typer.Option("output.wav", "-o", "--out", help="Output WAV filepath"),
    duration: float = typer.Option(3.0, "-d", "--duration", help="Render duration in seconds"),
    note: str = typer.Option("C3", "-n", "--note", help="MIDI note number (e.g. 60) or note name (e.g. C3, A4)"),
    velocity: float = typer.Option(0.85, "-v", "--velocity", help="Note velocity [0.0 - 1.0]"),
    sample_rate: int = typer.Option(44100, "-s", "--sample-rate", help="Audio sampling rate in Hz"),
):
    """Render a patch graph or preset to a WAV audio file."""
    graph = _resolve_graph(patch)
    graph.sample_rate = sample_rate

    # Parse note
    midi_note = int(note) if note.isdigit() else note_name_to_midi(note)

    console.print(f"[bold cyan]WaveForge Audio Renderer[/bold cyan]")
    console.print(f"Patch: [green]{graph.name}[/green] | Sample Rate: {sample_rate} Hz | Duration: {duration}s")
    console.print(f"Triggering Note: [yellow]{midi_to_note_name(midi_note)}[/yellow] (MIDI {midi_note})")

    engine = AudioEngine(graph)
    start_time = time.perf_counter()
    left, right = engine.render(duration_sec=duration, midi_note=midi_note, velocity=velocity)
    elapsed = time.perf_counter() - start_time

    write_wav(out, left, right, sample_rate=sample_rate, bit_depth=16)

    rt_factor = duration / elapsed if elapsed > 0 else 0
    console.print(f"[bold green][+][/bold green] Rendered to [bold white]{out}[/bold white] in [cyan]{elapsed:.3f}s[/cyan] ({rt_factor:.1f}x real-time speed)")


@app.command("play")
def play_command(
    patch: Optional[str] = typer.Argument(None, help="Path to patch JSON or preset name"),
    duration: float = typer.Option(2.5, "-d", "--duration", help="Playback duration in seconds"),
    note: str = typer.Option("C3", "-n", "--note", help="MIDI note name or number"),
    velocity: float = typer.Option(0.85, "-v", "--velocity", help="Note velocity [0.0 - 1.0]"),
):
    """Render and immediately play a patch through the audio output."""
    graph = _resolve_graph(patch)
    midi_note = int(note) if note.isdigit() else note_name_to_midi(note)

    console.print(f"[bold cyan]WaveForge Live Player[/bold cyan]")
    console.print(f"Playing patch: [green]{graph.name}[/green] ({duration}s at note {midi_to_note_name(midi_note)})...")

    engine = AudioEngine(graph)
    left, right = engine.render(duration_sec=duration, midi_note=midi_note, velocity=velocity)

    player = AudioPlayer(sample_rate=graph.sample_rate)
    played = player.play_buffer(left, right, sample_rate=graph.sample_rate, blocking=True)
    if played:
        console.print("[bold green][+] Playback complete[/bold green]")
    else:
        console.print("[bold yellow]No active audio output driver found on this system.[/bold yellow]")


@app.command("export-c")
def export_c_command(
    patch: Optional[str] = typer.Argument(None, help="Path to patch JSON or preset name"),
    out: str = typer.Option("waveforge_synth.h", "-o", "--out", help="Output C header file path"),
    guard: str = typer.Option("WAVEFORGE_SYNTH_H", "--guard", help="Header guard identifier"),
):
    """Transpile a patch into a zero-dependency standalone C99 header file."""
    graph = _resolve_graph(patch)
    generator = CCodeGenerator(graph)
    c_source = generator.generate_header(guard_name=guard)

    with open(out, "w", encoding="utf-8") as f:
        f.write(c_source)

    console.print(f"[bold green][+][/bold green] Standalone C99 header exported to [bold white]{out}[/bold white]")
    console.print(f"Includes self-contained mathematical PolyBLEP oscillators, RBJ biquad filters, and DSP evaluation loop.")


@app.command("compile-c")
def compile_c_command(
    patch: Optional[str] = typer.Argument(None, help="Path to patch JSON or preset name"),
    out: str = typer.Option("synth_runner.exe", "-o", "--out", help="Output binary name"),
):
    """Export patch to C and compile directly into a native executable with clang/gcc."""
    graph = _resolve_graph(patch)
    generator = CCodeGenerator(graph)
    c_source = generator.generate_header()

    console.print(f"Compiling [green]{graph.name}[/green] with native C compiler...")
    success, res = CCompilerDriver.compile_standalone_c(c_source, output_exe=out)
    if not success:
        console.print(f"[bold red]Compilation Failed:[/bold red]\n{res}")
        raise typer.Exit(code=1)

    console.print(f"[bold green][+] Successfully compiled:[/bold green] [bold white]{out}[/bold white]")

    console.print("Executing compiled synth test runner...")
    retcode, out_log = CCompilerDriver.run_standalone_exe(out)
    console.print(f"[cyan]{out_log.strip()}[/cyan]")
    if retcode == 0:
        console.print("[bold green][+] Native DSP execution test passed![/bold green]")
    else:
        console.print(f"[bold red]Executable returned exit code {retcode}[/bold red]")


@app.command("info")
def info_command(
    patch: Optional[str] = typer.Argument(None, help="Path to patch JSON or preset name"),
):
    """Display graph topology, node count, pin connections, and execution order."""
    graph = _resolve_graph(patch)
    order = graph.get_topological_sort()

    table = Table(title=f"WaveForge Patch: {graph.name}", show_header=True, header_style="bold magenta")
    table.add_column("Order", style="dim", width=6)
    table.add_column("Node ID", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Parameters", style="yellow")
    table.add_column("Connections In", style="white")

    conn_in: dict[str, list[str]] = {}
    for c in graph.connections:
        conn_in.setdefault(c.to_node, []).append(f"{c.from_node}.{c.from_pin} -> {c.to_pin}")

    for idx, nid in enumerate(order, start=1):
        node = graph.nodes[nid]
        p_str = ", ".join(f"{k}={v}" for k, v in list(node.params.items())[:3])
        if len(node.params) > 3:
            p_str += ", ..."
        cin_str = "\n".join(conn_in.get(nid, ["(none)"]))
        table.add_row(str(idx), nid, node.TYPE_ID, p_str, cin_str)

    console.print(table)
    console.print(f"Total Nodes: [bold]{len(graph.nodes)}[/bold] | Total Connections: [bold]{len(graph.connections)}[/bold]")


@app.command("list-nodes")
def list_nodes_command():
    """List all registered DSP node types and their terminal pins."""
    table = Table(title="Registered WaveForge DSP Nodes", show_header=True, header_style="bold cyan")
    table.add_column("Type ID", style="bold green", no_wrap=True)
    table.add_column("Display Name", style="white")
    table.add_column("Category", style="yellow")
    table.add_column("Inputs", style="dim")
    table.add_column("Outputs", style="dim")
    table.add_column("Description", style="italic")

    for type_id, cls in sorted(NODE_REGISTRY.items()):
        meta = cls.get_metadata()
        in_pins = ", ".join(p.name for p in meta.inputs) or "none"
        out_pins = ", ".join(p.name for p in meta.outputs) or "none"
        table.add_row(type_id, meta.display_name, meta.category, in_pins, out_pins, meta.description)

    console.print(table)


@app.command("list-presets")
def list_presets_command():
    """List all built-in production synthesizer presets."""
    table = Table(title="WaveForge Built-in Presets", show_header=True, header_style="bold magenta")
    table.add_column("Preset ID", style="bold green")
    table.add_column("Name", style="white")
    table.add_column("Nodes", style="cyan")

    for pid, factory in PRESET_CATALOG.items():
        g = factory()
        table.add_row(pid, g.name, str(len(g.nodes)))

    console.print(table)


@app.command("benchmark")
def benchmark_command(
    patch: Optional[str] = typer.Argument(None, help="Path to patch JSON or preset name"),
    seconds: float = typer.Option(10.0, "-s", "--seconds", help="Duration of simulated audio to benchmark"),
):
    """Benchmark DSP execution throughput, samples/sec, and Real-Time Factor."""
    graph = _resolve_graph(patch)
    engine = AudioEngine(graph)

    sample_rate = graph.sample_rate
    block_size = graph.block_size
    total_samples = int(seconds * sample_rate)
    num_blocks = total_samples // block_size

    console.print(f"[bold cyan]Benchmarking {graph.name}...[/bold cyan]")
    console.print(f"Simulating [yellow]{seconds:.1f}s[/yellow] of audio ({total_samples:,} samples, {num_blocks:,} blocks)")

    # Warmup
    for _ in range(50):
        engine.process_block()

    start = time.perf_counter()
    for _ in range(num_blocks):
        engine.process_block()
    elapsed = time.perf_counter() - start

    samples_per_sec = total_samples / elapsed
    msamples_per_sec = samples_per_sec / 1_000_000.0
    rt_factor = seconds / elapsed

    panel_content = (
        f"[bold white]Elapsed Time:[/bold white] {elapsed:.3f} s\n"
        f"[bold white]DSP Throughput:[/bold white] [bold green]{msamples_per_sec:.2f} Megasamples/sec[/bold green]\n"
        f"[bold white]Blocks/sec:[/bold white] {num_blocks / elapsed:,.0f}\n"
        f"[bold white]Real-Time Factor:[/bold white] [bold cyan]{rt_factor:.1f}x real-time speed[/bold cyan]"
    )
    console.print(Panel(panel_content, title="Benchmark Results", border_style="green"))


@app.command("studio")
def studio_command(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Bind host address"),
    port: int = typer.Option(8000, "--port", "-p", help="Bind port number"),
    reload: bool = typer.Option(False, "--reload", help="Enable uvicorn hot reloading"),
):
    """Launch the interactive WaveForge Web Studio."""
    import uvicorn
    console.print(f"[bold cyan]Launching WaveForge Web Studio at [underline]http://{host}:{port}[/underline][/bold cyan]")
    uvicorn.run("waveforge.studio.app:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    app()
