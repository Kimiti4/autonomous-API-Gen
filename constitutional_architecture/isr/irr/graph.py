"""
Requirement Graph.

Converts the IRR into a typed graph of requirement relationships.
This graph becomes the structured input to ISR construction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from constitutional_architecture.isr.irr.model import IRR, Requirement


@dataclass(frozen=True)
class RequirementNode:
    """A node in the requirement graph."""

    id: str
    label: str
    requirement_type: str
    priority: str = "must"
    attributes: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class RequirementEdge:
    """An edge in the requirement graph."""

    source_id: str
    target_id: str
    relationship: str
    description: str = ""


@dataclass(frozen=True)
class RequirementGraph:
    """
    A typed graph of requirement relationships.

    This is the bridge between the IRR (intent) and the ISR (architecture).
    """

    nodes: tuple[RequirementNode, ...] = ()
    edges: tuple[RequirementEdge, ...] = ()
    source_irr_id: str = ""

    def get_node(self, node_id: str) -> Optional[RequirementNode]:
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None


class RequirementGraphBuilder:
    """Builds a requirement graph from an IRR."""

    @staticmethod
    def from_irr(irr: IRR) -> RequirementGraph:
        nodes: list[RequirementNode] = []
        edges: list[RequirementEdge] = []

        for req in irr.requirements:
            nodes.append(RequirementNode(
                id=req.id,
                label=req.title,
                requirement_type=req.requirement_type.value,
                priority=req.priority.value,
            ))

            for related_id in req.related_requirements:
                edges.append(RequirementEdge(
                    source_id=req.id,
                    target_id=related_id,
                    relationship="relates_to",
                ))

        for i, concept in enumerate(irr.domain_concepts):
            concept_id = f"concept-{i}"
            nodes.append(RequirementNode(
                id=concept_id,
                label=concept,
                requirement_type="domain_concept",
            ))

        return RequirementGraph(
            nodes=tuple(nodes),
            edges=tuple(edges),
            source_irr_id=irr.id,
        )
