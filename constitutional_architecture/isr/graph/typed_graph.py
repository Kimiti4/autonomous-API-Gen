"""
Typed Directed Attributed Graph.

The ISR is internally represented as a typed, directed, attributed graph.
This module provides the core graph data structure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator, Optional

from constitutional_architecture.isr.model.edges import EdgeAttributes, EdgeType
from constitutional_architecture.isr.model.nodes import NodeType


@dataclass(frozen=True)
class GraphNode:
    """A node in the ISR graph."""
    id: str
    node_type: NodeType
    label: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)
    parent_id: Optional[str] = None


@dataclass(frozen=True)
class GraphEdge:
    """An edge in the ISR graph."""
    id: str
    source_id: str
    target_id: str
    edge_type: EdgeType
    attributes: EdgeAttributes = field(default_factory=EdgeAttributes)
    metadata: dict[str, Any] = field(default_factory=dict)


class TypedGraph:
    """
    A typed, directed, attributed graph representing the ISR.

    This is the internal representation used by the evolution engine,
    type checker, and compiler. It is constructed from the ISR model
    and can be serialized back.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, GraphNode] = {}
        self._edges: dict[str, GraphEdge] = {}
        self._adjacency: dict[str, list[str]] = {}
        self._reverse_adjacency: dict[str, list[str]] = {}

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        return len(self._edges)

    def add_node(self, node: GraphNode) -> None:
        if node.id in self._nodes:
            raise ValueError(f"Node '{node.id}' already exists")
        self._nodes[node.id] = node
        self._adjacency.setdefault(node.id, [])
        self._reverse_adjacency.setdefault(node.id, [])

    def add_edge(self, edge: GraphEdge) -> None:
        if edge.id in self._edges:
            raise ValueError(f"Edge '{edge.id}' already exists")
        if edge.source_id not in self._nodes:
            raise ValueError(f"Source node '{edge.source_id}' does not exist")
        if edge.target_id not in self._nodes:
            raise ValueError(f"Target node '{edge.target_id}' does not exist")
        self._edges[edge.id] = edge
        self._adjacency[edge.source_id].append(edge.id)
        self._reverse_adjacency[edge.target_id].append(edge.id)

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        return self._nodes.get(node_id)

    def get_edge(self, edge_id: str) -> Optional[GraphEdge]:
        return self._edges.get(edge_id)

    def get_nodes_by_type(self, node_type: NodeType) -> list[GraphNode]:
        return [n for n in self._nodes.values() if n.node_type == node_type]

    def get_edges_by_type(self, edge_type: EdgeType) -> list[GraphEdge]:
        return [e for e in self._edges.values() if e.edge_type == edge_type]

    def get_outgoing_edges(self, node_id: str) -> list[GraphEdge]:
        return [self._edges[eid] for eid in self._adjacency.get(node_id, [])]

    def get_incoming_edges(self, node_id: str) -> list[GraphEdge]:
        return [self._edges[eid] for eid in self._reverse_adjacency.get(node_id, [])]

    def has_edge(self, source_id: str, target_id: str, edge_type: EdgeType) -> bool:
        for edge_id in self._adjacency.get(source_id, []):
            edge = self._edges[edge_id]
            if edge.target_id == target_id and edge.edge_type == edge_type:
                return True
        return False

    def nodes(self) -> Iterator[GraphNode]:
        return iter(self._nodes.values())

    def edges(self) -> Iterator[GraphEdge]:
        return iter(self._edges.values())

    def clone(self) -> "TypedGraph":
        new_graph = TypedGraph()
        for node in self._nodes.values():
            new_graph.add_node(node)
        for edge in self._edges.values():
            new_graph.add_edge(edge)
        return new_graph