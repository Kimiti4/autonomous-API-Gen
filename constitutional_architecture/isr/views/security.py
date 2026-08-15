"""
Security View.

Projects the ISR graph into a security-focused view
consumed by the Security Engineer agent.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from constitutional_architecture.isr.graph.typed_graph import TypedGraph
from constitutional_architecture.isr.model.edges import EdgeType
from constitutional_architecture.isr.model.nodes import NodeType


@dataclass(frozen=True)
class SecurityView:
    """The security view of the ISR."""

    policies: tuple[dict, ...] = ()
    secured_interfaces: tuple[str, ...] = ()
    unsecured_interfaces: tuple[str, ...] = ()
    permissions_defined: tuple[str, ...] = ()
    permissions_referenced: tuple[str, ...] = ()
    undefined_permissions: tuple[str, ...] = ()
    coverage_ratio: float = 0.0


class SecurityViewBuilder:
    """Builds the security view from an ISR graph."""

    @staticmethod
    def build(graph: TypedGraph) -> SecurityView:
        policies = [
            {"id": n.id, "label": n.label, "attributes": n.attributes}
            for n in graph.get_nodes_by_type(NodeType.POLICY)
        ]

        interfaces = graph.get_nodes_by_type(NodeType.INTERFACE)
        secured: list[str] = []
        unsecured: list[str] = []

        for iface in interfaces:
            has_policy = any(
                e.edge_type == EdgeType.SECURED_BY
                for e in graph.get_outgoing_edges(iface.id)
            )
            if has_policy:
                secured.append(iface.id)
            else:
                unsecured.append(iface.id)

        permissions_defined = tuple(
            n.label for n in graph.get_nodes_by_type(NodeType.PERMISSION)
        )

        permissions_referenced: set[str] = set()
        for endpoint in graph.get_nodes_by_type(NodeType.ENDPOINT):
            perms = endpoint.attributes.get("required_permissions", [])
            permissions_referenced.update(perms)

        undefined = tuple(
            p for p in permissions_referenced if p not in set(permissions_defined)
        )

        total = len(interfaces)
        coverage = len(secured) / total if total > 0 else 0.0

        return SecurityView(
            policies=tuple(policies),
            secured_interfaces=tuple(secured),
            unsecured_interfaces=tuple(unsecured),
            permissions_defined=permissions_defined,
            permissions_referenced=tuple(permissions_referenced),
            undefined_permissions=undefined,
            coverage_ratio=coverage,
        )
