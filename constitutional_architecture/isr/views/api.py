"""
API View.

Projects the ISR graph into an API-focused view
consumed by the Backend and Frontend Engineer agents.
"""

from __future__ import annotations

from dataclasses import dataclass

from constitutional_architecture.isr.graph.typed_graph import TypedGraph
from constitutional_architecture.isr.model.nodes import NodeType


@dataclass(frozen=True)
class APIView:
    """The API view of the ISR."""

    interfaces: tuple[dict, ...] = ()
    endpoints: tuple[dict, ...] = ()
    total_endpoints: int = 0
    public_endpoints: int = 0
    internal_interfaces: int = 0


class APIViewBuilder:
    """Builds the API view from an ISR graph."""

    @staticmethod
    def build(graph: TypedGraph) -> APIView:
        interfaces = tuple(
            {"id": i.id, "label": i.label, "attributes": i.attributes}
            for i in graph.get_nodes_by_type(NodeType.INTERFACE)
        )
        endpoints = tuple(
            {"id": e.id, "label": e.label, "attributes": e.attributes}
            for e in graph.get_nodes_by_type(NodeType.ENDPOINT)
        )

        public_count = sum(
            1 for e in graph.get_nodes_by_type(NodeType.ENDPOINT)
            if e.attributes.get("is_public", False)
        )
        internal_count = sum(
            1 for i in graph.get_nodes_by_type(NodeType.INTERFACE)
            if i.attributes.get("is_internal", False)
        )

        return APIView(
            interfaces=interfaces,
            endpoints=endpoints,
            total_endpoints=len(endpoints),
            public_endpoints=public_count,
            internal_interfaces=internal_count,
        )
