"""
Complexity Metrics.

Computes architectural complexity from ISR graph properties.
"""

from __future__ import annotations

from constitutional_architecture.isr.graph.typed_graph import TypedGraph
from constitutional_architecture.isr.graph.traversal import GraphTraversal
from constitutional_architecture.isr.model.edges import EdgeType


class ComplexityMetrics:
    """Computes complexity metrics from the ISR graph."""

    @staticmethod
    def graph_density(graph: TypedGraph) -> float:
        n = graph.node_count
        if n <= 1:
            return 0.0
        max_edges = n * (n - 1)
        if max_edges == 0:
            return 0.0
        return graph.edge_count / max_edges

    @staticmethod
    def max_dependency_depth(graph: TypedGraph) -> int:
        try:
            sorted_nodes = GraphTraversal.topological_sort(graph, EdgeType.DEPENDS_ON)
            if not sorted_nodes:
                return 0

            depth: dict[str, int] = {n.id: 0 for n in sorted_nodes}
            for node in sorted_nodes:
                for edge in graph.get_outgoing_edges(node.id):
                    if edge.edge_type == EdgeType.DEPENDS_ON:
                        if edge.target_id in depth:
                            depth[edge.target_id] = max(
                                depth[edge.target_id],
                                depth[node.id] + 1,
                            )
            return max(depth.values()) if depth else 0
        except ValueError:
            return -1

    @staticmethod
    def node_count_by_type(graph: TypedGraph) -> dict[str, int]:
        counts: dict[str, int] = {}
        for node in graph.nodes():
            type_name = node.node_type.value
            counts[type_name] = counts.get(type_name, 0) + 1
        return counts

    @staticmethod
    def average_module_size(graph: TypedGraph) -> float:
        from constitutional_architecture.isr.model.nodes import NodeType

        modules = graph.get_nodes_by_type(NodeType.MODULE)
        if not modules:
            return 0.0

        total_entities = 0
        for module in modules:
            entities = [
                e for e in graph.get_outgoing_edges(module.id)
                if e.edge_type == EdgeType.OWNS
                and graph.get_node(e.target_id) is not None
                and graph.get_node(e.target_id).node_type == NodeType.ENTITY
            ]
            total_entities += len(entities)

        return total_entities / len(modules)

    @staticmethod
    def compute_complexity_score(graph: TypedGraph) -> float:
        density = ComplexityMetrics.graph_density(graph)
        depth = ComplexityMetrics.max_dependency_depth(graph)
        node_count = graph.node_count

        norm_depth = min(max(depth, 0) / 10.0, 1.0)
        norm_size = min(node_count / 200.0, 1.0)

        score = 0.4 * density + 0.3 * norm_depth + 0.3 * norm_size
        return min(max(score, 0.0), 1.0)
