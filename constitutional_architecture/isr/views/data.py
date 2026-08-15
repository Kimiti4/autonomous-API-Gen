"""
Data View.

Projects the ISR graph into a data-focused view
consumed by the Database Engineer agent.
"""

from __future__ import annotations

from dataclasses import dataclass

from constitutional_architecture.isr.graph.typed_graph import TypedGraph
from constitutional_architecture.isr.model.nodes import NodeType


@dataclass(frozen=True)
class DataView:
    """The data view of the ISR."""

    entities: tuple[dict, ...] = ()
    total_fields: int = 0
    total_relationships: int = 0
    aggregate_roots: tuple[str, ...] = ()
    value_objects: tuple[str, ...] = ()


class DataViewBuilder:
    """Builds the data view from an ISR graph."""

    @staticmethod
    def build(graph: TypedGraph) -> DataView:
        entities = tuple(
            {"id": e.id, "label": e.label, "attributes": e.attributes}
            for e in graph.get_nodes_by_type(NodeType.ENTITY)
        )
        fields = graph.get_nodes_by_type(NodeType.FIELD)

        aggregate_roots = tuple(
            e.id for e in graph.get_nodes_by_type(NodeType.ENTITY)
            if e.attributes.get("is_aggregate_root", False)
        )
        value_objects = tuple(
            e.id for e in graph.get_nodes_by_type(NodeType.ENTITY)
            if e.attributes.get("is_value_object", False)
        )

        return DataView(
            entities=entities,
            total_fields=len(fields),
            total_relationships=0,
            aggregate_roots=aggregate_roots,
            value_objects=value_objects,
        )
