"""
Cohesion Metrics.

Computes intra-module cohesion from the ISR graph.
"""

from __future__ import annotations

from constitutional_architecture.isr.graph.typed_graph import TypedGraph
from constitutional_architecture.isr.model.edges import EdgeType
from constitutional_architecture.isr.model.nodes import NodeType


class CohesionMetrics:
    """Computes cohesion metrics from the ISR graph."""

    @staticmethod
    def module_cohesion(graph: TypedGraph, module_id: str) -> float:
        owned_nodes: set[str] = set()
        for edge in graph.get_outgoing_edges(module_id):
            if edge.edge_type in {EdgeType.OWNS, EdgeType.CONTAINS}:
                owned_nodes.add(edge.target_id)

        if len(owned_nodes) <= 1:
            return 1.0

        internal_edges = 0
        total_possible = len(owned_nodes) * (len(owned_nodes) - 1)

        for node_id in owned_nodes:
            for edge in graph.get_outgoing_edges(node_id):
                if edge.target_id in owned_nodes:
                    internal_edges += 1

        if total_possible == 0:
            return 0.0

        return internal_edges / total_possible

    @staticmethod
    def average_cohesion(graph: TypedGraph) -> float:
        modules = graph.get_nodes_by_type(NodeType.MODULE)
        if not modules:
            return 0.0

        total = sum(CohesionMetrics.module_cohesion(graph, m.id) for m in modules)
        return total / len(modules)

    @staticmethod
    def compute_cohesion_score(graph: TypedGraph) -> float:
        return CohesionMetrics.average_cohesion(graph)
