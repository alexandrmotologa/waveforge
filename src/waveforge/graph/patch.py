"""Modular synthesizer patch graph, connection routing, and serialization."""

from __future__ import annotations
import json
from typing import Dict, List, Optional, Tuple, Any, Set
from collections import defaultdict, deque
from waveforge.core.config import (
    PatchSchema,
    NodeInstanceSchema,
    ConnectionSchema,
)
from waveforge.graph.node import BaseNode, NODE_REGISTRY


class NodeConnection:
    """Directed connection edge between source output pin and target input pin."""

    def __init__(self, from_node: str, from_pin: str, to_node: str, to_pin: str):
        self.from_node = from_node
        self.from_pin = from_pin
        self.to_node = to_node
        self.to_pin = to_pin

    def to_schema(self) -> ConnectionSchema:
        return ConnectionSchema(
            from_node=self.from_node,
            from_pin=self.from_pin,
            to_node=self.to_node,
            to_pin=self.to_pin,
        )

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, NodeConnection):
            return False
        return (
            self.from_node == other.from_node
            and self.from_pin == other.from_pin
            and self.to_node == other.to_node
            and self.to_pin == other.to_pin
        )

    def __repr__(self) -> str:
        return f"NodeConnection({self.from_node}.{self.from_pin} -> {self.to_node}.{self.to_pin})"


class NodeGraph:
    """Directed Acyclic Graph (DAG) representing the complete modular patch."""

    def __init__(
        self,
        name: str = "Untitled Patch",
        sample_rate: int = 44100,
        block_size: int = 128,
        author: str = "WaveForge",
    ):
        self.name = name
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.author = author

        self.nodes: Dict[str, BaseNode] = {}
        self.node_positions: Dict[str, Tuple[float, float]] = {}
        self.connections: List[NodeConnection] = []

    def add_node(
        self,
        type_id: str,
        node_id: Optional[str] = None,
        x: float = 0.0,
        y: float = 0.0,
        params: Optional[Dict[str, Any]] = None,
    ) -> BaseNode:
        """Instantiate and insert a DSP node into the graph."""
        if type_id not in NODE_REGISTRY:
            raise ValueError(f"Unknown node type: {type_id}. Available: {list(NODE_REGISTRY.keys())}")

        if node_id is None:
            # Auto-generate unique ID based on type
            existing_count = sum(1 for nid in self.nodes if nid.startswith(type_id))
            node_id = f"{type_id}_{existing_count + 1}"

        if node_id in self.nodes:
            raise ValueError(f"Node with ID '{node_id}' already exists in graph.")

        node_cls = NODE_REGISTRY[type_id]
        node = node_cls(node_id=node_id, sample_rate=self.sample_rate, params=params)
        self.nodes[node_id] = node
        self.node_positions[node_id] = (x, y)
        return node

    def remove_node(self, node_id: str) -> None:
        """Remove a node and all attached patch cables."""
        if node_id not in self.nodes:
            return

        del self.nodes[node_id]
        self.node_positions.pop(node_id, None)

        # Remove all connections involving this node
        self.connections = [
            c for c in self.connections if c.from_node != node_id and c.to_node != node_id
        ]

    def connect(
        self,
        from_node: str,
        from_pin: str,
        to_node: str,
        to_pin: str,
    ) -> NodeConnection:
        """Connect source output pin to target input pin."""
        if from_node not in self.nodes:
            raise KeyError(f"Source node '{from_node}' does not exist.")
        if to_node not in self.nodes:
            raise KeyError(f"Target node '{to_node}' does not exist.")

        src = self.nodes[from_node]
        tgt = self.nodes[to_node]

        if from_pin not in src.output_pins:
            raise KeyError(f"Source pin '{from_pin}' not found on {from_node}. Available: {list(src.output_pins.keys())}")
        if to_pin not in tgt.input_pins:
            raise KeyError(f"Target pin '{to_pin}' not found on {to_node}. Available: {list(tgt.input_pins.keys())}")

        conn = NodeConnection(from_node, from_pin, to_node, to_pin)
        # Avoid duplicate connections to same target pin
        self.connections = [c for c in self.connections if not (c.to_node == to_node and c.to_pin == to_pin)]
        self.connections.append(conn)
        return conn

    def disconnect(
        self,
        from_node: str,
        from_pin: str,
        to_node: str,
        to_pin: str,
    ) -> bool:
        """Remove an existing connection."""
        target = NodeConnection(from_node, from_pin, to_node, to_pin)
        initial_len = len(self.connections)
        self.connections = [c for c in self.connections if c != target]
        return len(self.connections) < initial_len

    def get_topological_sort(self) -> List[str]:
        """Compute execution order of nodes using Kahn's algorithm."""
        in_degree: Dict[str, int] = {node_id: 0 for node_id in self.nodes}
        adj: Dict[str, List[str]] = defaultdict(list)

        for c in self.connections:
            if c.from_node in self.nodes and c.to_node in self.nodes:
                adj[c.from_node].append(c.to_node)
                in_degree[c.to_node] += 1

        queue = deque([node_id for node_id, deg in in_degree.items() if deg == 0])
        sorted_nodes: List[str] = []

        while queue:
            curr = queue.popleft()
            sorted_nodes.append(curr)

            for neighbor in adj[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(sorted_nodes) < len(self.nodes):
            # Graph has cycle; fallback: append unvisited nodes to avoid dropping nodes
            remaining = [nid for nid in self.nodes if nid not in sorted_nodes]
            sorted_nodes.extend(remaining)

        return sorted_nodes

    def to_schema(self) -> PatchSchema:
        """Convert graph to Pydantic serializable schema."""
        nodes_schema = []
        for nid, node in self.nodes.items():
            pos = self.node_positions.get(nid, (0.0, 0.0))
            nodes_schema.append(
                NodeInstanceSchema(
                    id=nid,
                    type_id=node.TYPE_ID,
                    x=pos[0],
                    y=pos[1],
                    params=dict(node.params),
                )
            )

        conns_schema = [c.to_schema() for c in self.connections]

        return PatchSchema(
            name=self.name,
            author=self.author,
            sample_rate=self.sample_rate,
            block_size=self.block_size,
            nodes=nodes_schema,
            connections=conns_schema,
        )

    def to_dict(self) -> Dict[str, Any]:
        return self.to_schema().model_dump()

    def to_json(self, indent: int = 2) -> str:
        return self.to_schema().model_dump_json(indent=indent)

    @classmethod
    def from_schema(cls, schema: PatchSchema) -> NodeGraph:
        graph = cls(
            name=schema.name,
            sample_rate=schema.sample_rate,
            block_size=schema.block_size,
            author=schema.author,
        )

        for n in schema.nodes:
            graph.add_node(
                type_id=n.type_id,
                node_id=n.id,
                x=n.x,
                y=n.y,
                params=n.params,
            )

        for c in schema.connections:
            try:
                graph.connect(c.from_node, c.from_pin, c.to_node, c.to_pin)
            except KeyError:
                pass

        return graph

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> NodeGraph:
        schema = PatchSchema.model_validate(data)
        return cls.from_schema(schema)

    @classmethod
    def from_json(cls, json_str: str) -> NodeGraph:
        schema = PatchSchema.model_validate_json(json_str)
        return cls.from_schema(schema)

    def save(self, filepath: str) -> None:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.to_json())

    @classmethod
    def load(cls, filepath: str) -> NodeGraph:
        with open(filepath, "r", encoding="utf-8") as f:
            return cls.from_json(f.read())
