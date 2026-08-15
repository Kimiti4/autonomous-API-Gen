"""
Coupling Metrics.

Computes inter-module and inter-service coupling from the ISR graph.
"""

from __future__ import annotations

from constitutional_architecture.isr.graph.typed_graph import TypedGraph
from constitutional_architecture.isr.model.edges import EdgeType
from constitutional_architecture.isr.model.nodes import NodeType


class CouplingMetrics:
    """Computes coupling metrics from the ISR graph."""

    @staticmethod
    def inter_module_coupling(graph: TypedGraph) -> float:
        modules = graph.get_nodes_by_type(NodeType.MODULE)
        if len(modules) <= 1:
            return 0.0

        node_to_module: dict[str, str] = {}
        for module in modules:
            for edge in graph.get_outgoing_edges(module.id):
                if edge.edge_type in {EdgeType.OWNS, EdgeType.CONTAINS}:
                    node_to_module[edge.target_id] = module.id

        cross_module = 0
        total_deps = 0
        for edge in graph.get_edges_by_type(EdgeType.DEPENDS_ON):
            source_module = node_to_module.get(edge.source_id)
            target_module = node_to_module.get(edge.target_id)
            if source_module and target_module:
                total_deps += 1
                if source_module != target_module:
                    cross_module += 1

        if total_deps == 0:
            return 0.0
        return cross_module / total_deps

    @staticmethod
    def afferent_coupling(graph: TypedGraph, node_id: str) -> int:
        return len([
            e for e in graph.get_incoming_edges(node_id)
            if e.edge_type == EdgeType.DEPENDS_ON
        ])

    @staticmethod
    def efferent_coupling(graph: TypedGraph, node_id: str) -> int:
        return len([
            e for e in graph.get_outgoing_edges(node_id)
            if e.edge_type == EdgeType.DEPENDS_ON
        ])

    @staticmethod
    def instability_index(graph: TypedGraph, node_id: str) -> float:
        ca = CouplingMetrics.afferent_coupling(graph, node_id)
        ce = CouplingMetrics.efferent_coupling(graph, node_id)
        if ca + ce == 0:
            return 0.0
        return ce / (ca + ce)

    @staticmethod
    def compute_coupling_score(graph: TypedGraph) -> float:
        inter_module = CouplingMetrics.inter_module_coupling(graph)

        services = graph.get_nodes_by_type(NodeType.SERVICE)
        if services:
            avg_instability = sum(
                CouplingMetrics.instability_index(graph, s.id) for s in services
            ) / len(services)
        else:
            avg_instability = 0.0

        return 0.6 * inter_module + 0.4 * avg_instability
