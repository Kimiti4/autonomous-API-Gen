"""Genesis Mapper — deterministic derivation of ISR₀ from a Requirement Graph."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from isr.core.graph import Edge, EdgeType, ISRGraph, Node, NodeType
from reqgraph.core.graph import RequirementGraph, RequirementKind
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
