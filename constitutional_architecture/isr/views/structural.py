"""
Structural View.

Projects the ISR graph into a module-relationship view
consumed by the Software Architect agent.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from constitutional_architecture.isr.graph.typed_graph import TypedGraph
from constitutional_architecture.isr.model.edges import EdgeType
from constitutional_architecture.isr.model.nodes import NodeType


@dataclass(frozen=True)
class ModuleSummary:
    """Summary of a module in the structural view."""

    id: str
    name: str
    entity_count: int = 0
    service_count: int = 0
    interface_count: int = 0
    dependencies: tuple[str, ...] = ()
    dependents: tuple[str, ...] = ()


@dataclass(frozen=True)
class StructuralView:
    """The structural view of the ISR."""

    modules: tuple[ModuleSummary, ...] = ()
    total_entities: int = 0
    total_services: int = 0
    total_interfaces: int = 0
    dependency_count: int = 0


class StructuralViewBuilder:
    """Builds the structural view from an ISR graph."""

    @staticmethod
    def build(graph: TypedGraph) -> StructuralView:
        modules: list[ModuleSummary] = []
        module_nodes = graph.get_nodes_by_type(NodeType.MODULE)

        for module in module_nodes:
            owned = graph.get_outgoing_edges(module.id)
            entities = sum(
                1 for e in owned
                if e.edge_type == EdgeType.OWNS
                and graph.get_node(e.target_id) is not None
                and graph.get_node(e.target_id).node_type == NodeType.ENTITY
            )
            services = sum(
                1 for e in owned
                if e.edge_type == EdgeType.OWNS
                and graph.get_node(e.target_id) is not None
                and graph.get_node(e.target_id).node_type == NodeType.SERVICE
            )
            interfaces = sum(
                1 for e in owned
                if e.edge_type == EdgeType.OWNS
                and graph.get_node(e.target_id) is not None
                and graph.get_node(e.target_id).node_type == NodeType.INTERFACE
            )

            deps = tuple(
                e.target_id for e in graph.get_outgoing_edges(module.id)
                if e.edge_type == EdgeType.DEPENDS_ON
            )
            dependents = tuple(
                e.source_id for e in graph.get_incoming_edges(module.id)
                if e.edge_type == EdgeType.DEPENDS_ON
            )

            modules.append(ModuleSummary(
                id=module.id,
                name=module.label,
                entity_count=entities,
                service_count=services,
                interface_count=interfaces,
                dependencies=deps,
                dependents=dependents,
            ))

        return StructuralView(
            modules=tuple(modules),
            total_entities=len(graph.get_nodes_by_type(NodeType.ENTITY)),
            total_services=len(graph.get_nodes_by_type(NodeType.SERVICE)),
            total_interfaces=len(graph.get_nodes_by_type(NodeType.INTERFACE)),
            dependency_count=len(graph.get_edges_by_type(EdgeType.DEPENDS_ON)),
        )
