"""Genesis Mapper — deterministic derivation of ISR₀ from a Requirement Graph."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from isr.core.graph import EDGE_TYPE_COMPATIBILITY, Edge, EdgeType, ISRGraph, Node, NodeType
from reqgraph.core.graph import RequirementEdgeType, RequirementGraph, RequirementKind
from genesis.evidence import CoverageReport

CONSTITUTIONAL_DEFAULTS = (
    "security",
    "observability",
    "testing",
    "deployment",
    "documentation",
)


@dataclass(frozen=True)
class GenesisResult:
    graph: ISRGraph
    coverage: CoverageReport
    defaults: list[str]


class GenesisMapper(Protocol):
    def map(
        self, req: RequirementGraph, mapping_spec_version: str
    ) -> GenesisResult: ...


class ReferenceDeterministicMapper:
    """Deterministic seed mapper.

    Produces a neutral, valid ISR₀; architectural decisions are left to the
    v1.3 evolution genome.  The mapping is pure and reproducible: identical
    RequirementGraph + identical mapping_spec_version → identical ISRGraph.
    """

    def map(
        self, req: RequirementGraph, mapping_spec_version: str
    ) -> GenesisResult:
        nodes: dict[str, Node] = {}
        coverage: dict[str, list[str]] = {}

        for n in sorted(req.nodes.values(), key=lambda x: x.id):
            # Preserve every authoritative requirement as a first-class ISR ref,
            # independently of its architecture projection.
            ref_id = f"requirement_ref:{n.id}"
            nodes[ref_id] = Node(
                id=ref_id,
                type=NodeType.REQUIREMENT_REF,
                properties={
                    "ref_id": n.id,
                    "requirement_id": n.id,
                    "semantic_content": n.statement,
                    "statement": n.statement,
                    "requirement_kind": n.kind.value,
                    "priority": n.priority.value,
                    "acceptance_criteria": list(n.acceptance_criteria),
                    "source_refs": list(n.source_refs),
                    "resolution_ref": n.resolution_ref,
                    "properties": dict(n.properties),
                },
            )
            coverage.setdefault(n.id, []).append(ref_id)

            if n.kind is RequirementKind.DOMAIN_CONCEPT:
                target_type = NodeType.DOMAIN
            elif n.kind is RequirementKind.FUNCTIONAL:
                target_type = NodeType.CAPABILITY
            elif n.kind is RequirementKind.NON_FUNCTIONAL:
                target_type = NodeType.SERVICE
            elif n.kind is RequirementKind.CONSTRAINT:
                target_type = NodeType.SECURITY_POLICY
            else:
                continue

            node_id = f"{target_type.value}:{n.id}"
            nodes[node_id] = Node(
                id=node_id,
                type=target_type,
                properties={"label": n.statement, "priority": n.priority.value},
            )
            coverage.setdefault(n.id, []).append(node_id)

        # Explicit architecture fragments are accepted only when they are
        # declared in the authoritative requirement properties. This is a
        # typed source-to-ISR projection surface, not an inference mechanism.
        declared_nodes: dict[str, Node] = {}
        declared_edges: dict[str, Edge] = {}
        known_requirement_ids = set(req.nodes)
        for requirement in sorted(req.nodes.values(), key=lambda item: item.id):
            raw_nodes = requirement.properties.get("isr_nodes", [])
            raw_edges = requirement.properties.get("isr_edges", [])
            if not isinstance(raw_nodes, (list, tuple)) or not isinstance(raw_edges, (list, tuple)):
                raise ValueError(
                    f"requirement {requirement.id!r} isr_nodes/isr_edges must be lists"
                )
            for declaration in raw_nodes:
                if not isinstance(declaration, dict):
                    raise ValueError(f"requirement {requirement.id!r} has a malformed ISR node declaration")
                node_id, raw_type, raw_properties = (
                    declaration.get("id"), declaration.get("type"), declaration.get("properties")
                )
                if not isinstance(node_id, str) or not node_id or not isinstance(raw_type, str) or not isinstance(raw_properties, dict):
                    raise ValueError(f"requirement {requirement.id!r} ISR node needs id/type/properties")
                try:
                    node_type = NodeType(raw_type)
                except ValueError as exc:
                    raise ValueError(f"ISR node {node_id!r} has unsupported type {raw_type!r}") from exc
                source_ids = raw_properties.get("source_requirement_ids")
                if (
                    not isinstance(source_ids, (list, tuple)) or not source_ids
                    or any(not isinstance(source_id, str) or source_id not in known_requirement_ids for source_id in source_ids)
                    or requirement.id not in source_ids
                ):
                    raise ValueError(
                        f"ISR node {node_id!r} must cite known source_requirement_ids including {requirement.id!r}"
                    )
                if node_id in nodes or node_id in declared_nodes:
                    raise ValueError(f"duplicate ISR node declaration: {node_id!r}")
                declared_nodes[node_id] = Node(
                    id=node_id, type=node_type, properties=dict(raw_properties)
                )
            for declaration in raw_edges:
                if not isinstance(declaration, dict):
                    raise ValueError(f"requirement {requirement.id!r} has a malformed ISR edge declaration")
                edge_id, raw_type = declaration.get("id"), declaration.get("type")
                source_id, target_id = declaration.get("source_id"), declaration.get("target_id")
                raw_properties = declaration.get("properties", {})
                if not all(isinstance(value, str) and value for value in (edge_id, raw_type, source_id, target_id)) or not isinstance(raw_properties, dict):
                    raise ValueError(f"requirement {requirement.id!r} ISR edge needs id/type/endpoints/properties")
                try:
                    edge_type = EdgeType(raw_type)
                except ValueError as exc:
                    raise ValueError(f"ISR edge {edge_id!r} has unsupported type {raw_type!r}") from exc
                source_ids = raw_properties.get("source_requirement_ids")
                if (
                    not isinstance(source_ids, (list, tuple)) or not source_ids
                    or any(not isinstance(source_id, str) or source_id not in known_requirement_ids for source_id in source_ids)
                    or requirement.id not in source_ids
                ):
                    raise ValueError(
                        f"ISR edge {edge_id!r} must cite known source_requirement_ids including {requirement.id!r}"
                    )
                if edge_id in declared_edges:
                    raise ValueError(f"duplicate ISR edge declaration: {edge_id!r}")
                declared_edges[edge_id] = Edge(
                    id=edge_id, type=edge_type, source_id=source_id,
                    target_id=target_id, properties=dict(raw_properties),
                )

        nodes.update(declared_nodes)

        for default in CONSTITUTIONAL_DEFAULTS:
            node_id = f"service:constitution:{default}"
            nodes[node_id] = Node(
                id=node_id,
                type=NodeType.SERVICE,
                properties={
                    "label": f"constitutional baseline: {default}",
                    "derivation_ref": f"constitution:{default}",
                },
            )

        edges = {}
        for n in sorted(req.nodes.values(), key=lambda x: x.id):
            if n.kind is RequirementKind.FUNCTIONAL:
                capability_id = f"capability:{n.id}"
                ref_id = f"requirement_ref:{n.id}"
                if capability_id in nodes and ref_id in nodes:
                    edge_id = f"satisfies:{n.id}"
                    edges[edge_id] = Edge(
                        id=edge_id,
                        type=EdgeType.SATISFIES,
                        source_id=capability_id,
                        target_id=ref_id,
                    )

        relationship_types = {
            RequirementEdgeType.DEPENDS_ON: EdgeType.REQUIREMENT_DEPENDS_ON,
            RequirementEdgeType.CONFLICTS_WITH: EdgeType.REQUIREMENT_CONFLICTS_WITH,
            RequirementEdgeType.REFINES: EdgeType.REQUIREMENT_REFINES,
            RequirementEdgeType.OWNED_BY: EdgeType.REQUIREMENT_OWNED_BY,
        }
        for requirement_edge in sorted(req.edges.values(), key=lambda edge: edge.id):
            edge_type = relationship_types[requirement_edge.type]
            source_id = f"requirement_ref:{requirement_edge.source_id}"
            target_id = f"requirement_ref:{requirement_edge.target_id}"
            if source_id not in nodes or target_id not in nodes:
                # A malformed requirement graph must not be partially projected.
                raise ValueError(
                    f"requirement relationship {requirement_edge.id!r} has an unknown endpoint"
                )
            edges[f"requirement:{requirement_edge.id}"] = Edge(
                id=f"requirement:{requirement_edge.id}",
                type=edge_type,
                source_id=source_id,
                target_id=target_id,
                properties={
                    "source_requirement_edge_id": requirement_edge.id,
                    "resolution_ref": requirement_edge.resolution_ref,
                },
            )
        for edge_id, edge in declared_edges.items():
            if edge_id in edges:
                raise ValueError(f"duplicate ISR edge declaration: {edge_id!r}")
            if edge.source_id not in nodes or edge.target_id not in nodes:
                raise ValueError(
                    f"ISR edge {edge_id!r} references an unknown endpoint"
                )
            allowed = EDGE_TYPE_COMPATIBILITY.get(edge.type)
            if allowed and (
                nodes[edge.source_id].type not in allowed[0]
                or nodes[edge.target_id].type not in allowed[1]
            ):
                raise ValueError(
                    f"ISR edge {edge_id!r} has incompatible endpoint types for {edge.type.value!r}"
                )
            edges[edge_id] = edge

        graph = ISRGraph(nodes=nodes, edges=edges)

        uncovered = [
            n.id for n in req.nodes.values()
            if n.id not in coverage
        ]

        return GenesisResult(
            graph=graph,
            coverage=CoverageReport(
                requirement_to_isr=coverage,
                uncovered=uncovered,
            ),
            defaults=list(CONSTITUTIONAL_DEFAULTS),
        )
