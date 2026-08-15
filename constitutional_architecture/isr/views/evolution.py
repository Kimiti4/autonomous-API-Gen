"""
Evolution View.

Projects the ISR graph into an evolution-focused view
consumed by the Evolution Coordinator agent.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from constitutional_architecture.isr.graph.typed_graph import TypedGraph
from constitutional_architecture.isr.model.nodes import NodeType


@dataclass(frozen=True)
class EvolutionView:
    """The evolution view of the ISR."""

    mutable_regions: tuple[str, ...] = ()
    protected_regions: tuple[str, ...] = ()
    fitness_annotations: dict[str, float] = field(default_factory=dict)
    total_nodes: int = 0
    total_edges: int = 0
    node_type_distribution: dict[str, int] = field(default_factory=dict)


class EvolutionViewBuilder:
    """Builds the evolution view from an ISR graph."""

    @staticmethod
    def build(graph: TypedGraph) -> EvolutionView:
        mutable = tuple(
            n.id for n in graph.nodes()
            if n.node_type in {NodeType.SERVICE, NodeType.WORKFLOW, NodeType.INTERFACE}
        )

        protected = tuple(
            n.id for n in graph.nodes()
            if n.node_type in {NodeType.SYSTEM, NodeType.DEPLOYMENT}
        )

        distribution: dict[str, int] = {}
        for node in graph.nodes():
            type_name = node.node_type.value
            distribution[type_name] = distribution.get(type_name, 0) + 1

        return EvolutionView(
            mutable_regions=mutable,
            protected_regions=protected,
            total_nodes=graph.node_count,
            total_edges=graph.edge_count,
            node_type_distribution=distribution,
        )
