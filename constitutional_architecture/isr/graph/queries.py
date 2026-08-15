"""
Graph Query Operations.

Provides high-level query operations over the ISR graph.
"""

from __future__ import annotations

from typing import Optional

from constitutional_architecture.isr.graph.typed_graph import GraphNode, TypedGraph
from constitutional_architecture.isr.model.edges import EdgeType
from constitutional_architecture.isr.model.nodes import NodeType


class GraphQueries:
    """High-level query operations for the ISR graph."""

    @staticmethod
    def find_modules(graph: TypedGraph) -> list[GraphNode]:
        return graph.get_nodes_by_type(NodeType.MODULE)

    @staticmethod
    def find_services(graph: TypedGraph) -> list[GraphNode]:
        return graph.get_nodes_by_type(NodeType.SERVICE)

    @staticmethod
    def find_entities(graph: TypedGraph) -> list[GraphNode]:
        return graph.get_nodes_by_type(NodeType.ENTITY)

    @staticmethod
    def find_dependencies(graph: TypedGraph, node_id: str) -> list[GraphNode]:
        dependencies: list[GraphNode] = []
        for edge in graph.get_outgoing_edges(node_id):
            if edge.edge_type == EdgeType.DEPENDS_ON:
                target = graph.get_node(edge.target_id)
                if target:
                    dependencies.append(target)
        return dependencies

    @staticmethod
    def find_dependents(graph: TypedGraph, node_id: str) -> list[GraphNode]:
        dependents: list[GraphNode] = []
        for edge in graph.get_incoming_edges(node_id):
            if edge.edge_type == EdgeType.DEPENDS_ON:
                source = graph.get_node(edge.source_id)
                if source:
                    dependents.append(source)
        return dependents

    @staticmethod
    def find_orphaned_nodes(graph: TypedGraph) -> list[GraphNode]:
        orphans: list[GraphNode] = []
        for node in graph.nodes():
            if (not graph.get_outgoing_edges(node.id) and
                    not graph.get_incoming_edges(node.id)):
                orphans.append(node)
        return orphans

    @staticmethod
    def compute_in_degree(graph: TypedGraph, node_id: str) -> int:
        return len(graph.get_incoming_edges(node_id))

    @staticmethod
    def compute_out_degree(graph: TypedGraph, node_id: str) -> int:
        return len(graph.get_outgoing_edges(node_id))

    @staticmethod
    def find_nodes_by_label(graph: TypedGraph, label: str) -> list[GraphNode]:
        label_lower = label.lower()
        return [n for n in graph.nodes() if n.label.lower() == label_lower]

    @staticmethod
    def get_subgraph(
        graph: TypedGraph,
        root_id: str,
        max_depth: int = -1,
    ) -> TypedGraph:
        subgraph = TypedGraph()
        visited: set[str] = set()
        queue: list[tuple[str, int]] = [(root_id, 0)]

        while queue:
            node_id, depth = queue.pop(0)
            if node_id in visited:
                continue
            if max_depth >= 0 and depth > max_depth:
                continue
            visited.add(node_id)

            node = graph.get_node(node_id)
            if node:
                subgraph.add_node(node)

            for edge in graph.get_outgoing_edges(node_id):
                target = graph.get_node(edge.target_id)
                if target:
                    subgraph.add_node(target)
                    subgraph.add_edge(edge)
                    queue.append((edge.target_id, depth + 1))

        return subgraph
