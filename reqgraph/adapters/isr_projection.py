"""Project approved structured requirements into explicit ISR requirement refs.

This adapter deliberately does not create capabilities or SATISFIES edges.
A requirement reference is an obligation, not evidence that the obligation has
already been implemented.
"""
from __future__ import annotations

from reqgraph.core.graph import RequirementEdgeType, RequirementGraph
from reqgraph.core.invariants import validate_requirement_graph
from isr.core.graph import Edge, EdgeType, ISRGraph, Node, NodeType
from isr.core.invariants import validate_invariants


_EDGE_MAP = {
    RequirementEdgeType.DEPENDS_ON: EdgeType.REQUIREMENT_DEPENDS_ON,
    RequirementEdgeType.CONFLICTS_WITH: EdgeType.REQUIREMENT_CONFLICTS_WITH,
    RequirementEdgeType.REFINES: EdgeType.REQUIREMENT_REFINES,
    RequirementEdgeType.OWNED_BY: EdgeType.REQUIREMENT_OWNED_BY,
}


def project_requirement_graph(requirements: RequirementGraph) -> ISRGraph:
    """Create only requirement_ref nodes and preserved requirement relationships."""
    validate_requirement_graph(requirements)
    nodes: dict[str, Node] = {}
    edges: dict[str, Edge] = {}

    for requirement_id, requirement in requirements.nodes.items():
        node_id = f"requirement_ref:{requirement_id}"
        nodes[node_id] = Node(
            id=node_id,
            type=NodeType.REQUIREMENT_REF,
            properties={
                "ref_id": requirement_id,
                "statement": requirement.statement,
                "kind": requirement.kind.value,
                "priority": requirement.priority.value,
                "acceptance_criteria": list(requirement.acceptance_criteria),
                "source_refs": list(requirement.source_refs),
                "review_status": requirement.properties.get("review_status", "unknown"),
                "reviewer_id": requirement.properties.get("reviewer_id", ""),
                "approval_ref": requirement.properties.get("approval_ref", ""),
                "source_sha256": requirement.properties.get("source_sha256", ""),
                "ambiguity_score": requirement.ambiguity_score,
                "resolution_ref": requirement.resolution_ref or "",
            },
        )

    for edge_id, edge in requirements.edges.items():
        mapped_type = _EDGE_MAP[edge.type]
        source_id = f"requirement_ref:{edge.source_id}"
        target_id = f"requirement_ref:{edge.target_id}"
        edges[f"requirement_edge:{edge_id}"] = Edge(
            id=f"requirement_edge:{edge_id}",
            type=mapped_type,
            source_id=source_id,
            target_id=target_id,
            properties={"resolution_ref": edge.resolution_ref or ""},
        )

    projected = ISRGraph(nodes=nodes, edges=edges)
    validate_invariants(projected)
    return projected


def merge_requirement_projection(base: ISRGraph, requirements: RequirementGraph) -> ISRGraph:
    """Merge approved requirement refs into an architecture graph without overwrites."""
    projected = project_requirement_graph(requirements)
    node_collisions = sorted(set(base.nodes) & set(projected.nodes))
    edge_collisions = sorted(set(base.edges) & set(projected.edges))
    if node_collisions or edge_collisions:
        raise ValueError(
            f"requirement projection ID collision; nodes={node_collisions}, edges={edge_collisions}"
        )
    merged = ISRGraph(
        nodes={**base.nodes, **projected.nodes},
        edges={**base.edges, **projected.edges},
    )
    validate_invariants(merged)
    return merged
