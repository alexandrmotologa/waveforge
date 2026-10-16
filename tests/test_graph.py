"""Tests for NodeGraph creation, wiring, DAG topological sort, and serialization."""

import pytest
from waveforge.graph.patch import NodeGraph, NodeConnection


def test_graph_add_connect_nodes():
    g = NodeGraph(name="Synth DAG")
    osc = g.add_node("oscillator", "osc1", params={"frequency": 440.0})
    flt = g.add_node("biquad_filter", "flt1")
    out = g.add_node("audio_output", "out1")

    assert len(g.nodes) == 3
    conn1 = g.connect("osc1", "out", "flt1", "in")
    conn2 = g.connect("flt1", "out", "out1", "left")

    assert len(g.connections) == 2
    assert conn1.from_node == "osc1"
    assert conn2.to_node == "out1"


def test_graph_topological_sort():
    g = NodeGraph()
    g.add_node("audio_output", "out1")
    g.add_node("biquad_filter", "flt1")
    g.add_node("oscillator", "osc1")

    g.connect("osc1", "out", "flt1", "in")
    g.connect("flt1", "out", "out1", "left")

    order = g.get_topological_sort()
    # osc1 must precede flt1, flt1 must precede out1
    assert order.index("osc1") < order.index("flt1")
    assert order.index("flt1") < order.index("out1")


def test_graph_serialization_roundtrip():
    g = NodeGraph(name="Preset 1")
    g.add_node("oscillator", "osc1", x=100, y=200, params={"waveform": "square"})
    g.add_node("audio_output", "out1", x=400, y=200)
    g.connect("osc1", "out", "out1", "left")

    json_str = g.to_json()
    g2 = NodeGraph.from_json(json_str)

    assert g2.name == "Preset 1"
    assert "osc1" in g2.nodes
    assert g2.nodes["osc1"].params["waveform"] == "square"
    assert len(g2.connections) == 1
    assert g2.connections[0].from_node == "osc1"
