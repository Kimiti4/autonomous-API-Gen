"""Constituency/completeness invariants for the Requirement Graph."""

from __future__ import annotations

import re
from typing import Sequence

from reqgraph.core.graph import RequirementEdgeType, RequirementGraph, RequirementKind

AMBIGUITY_THRESHOLD = 0.5

FORBIDDEN_IMPLEMENTATION_TERMS: Sequence[str] = (
    "aws", "boto", "docker", "django", "fastapi", "flask", "graphql",
    "grpc", "java", "kafka", "kubernetes", "mongo", "mysql", "nestjs",
    "neo4j", "nginx", "nodejs", "postgres", "postgresql", "rabbitmq",
    "react", "redis", "spring", "terraform", "vue",
)

_LEAKAGE_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(t) for t in FORBIDDEN_IMPLEMENTATION_TERMS) + r")\b",
    re.IGNORECASE,
)


class RequirementInvariantViolation(Exception):
    pass


def validate_requirement_graph(graph: RequirementGraph) -> None:
    """Enforces consistency/completeness invariants.  Fail-closed."""

    node_ids = set(graph.nodes.keys())

    for edge in graph.edges.values():
        if edge.source_id not in node_ids:
            raise RequirementInvariantViolation(
                f"Edge '{edge.id}' references missing source node '{edge.source_id}'"
            )
        if edge.target_id not in node_ids:
            raise RequirementInvariantViolation(
                f"Edge '{edge.id}' references missing target node '{edge.target_id}'"
            )
        if edge.type is RequirementEdgeType.CONFLICTS_WITH and not edge.resolution_ref:
            raise RequirementInvariantViolation(
                f"Conflict edge '{edge.id}' is unresolved (no resolution_ref)"
            )

    for node in graph.nodes.values():
        if node.kind is RequirementKind.FUNCTIONAL and not node.acceptance_criteria:
            raise RequirementInvariantViolation(
                f"Requirement '{node.id}' is functional but lacks acceptance criteria"
            )
        if node.ambiguity_score > AMBIGUITY_THRESHOLD and not node.resolution_ref:
            raise RequirementInvariantViolation(
                f"Requirement '{node.id}' has ambiguity {node.ambiguity_score} "
                f"exceeding threshold {AMBIGUITY_THRESHOLD} but lacks resolution_ref"
            )
        _check_leakage(node.id, node.properties)
        for criterion in node.acceptance_criteria:
            if _LEAKAGE_RE.search(str(criterion)):
                match = _LEAKAGE_RE.search(str(criterion)).group().lower()
                raise RequirementInvariantViolation(
                    f"Implementation leakage in acceptance criteria of '{node.id}': '{match}'"
                )


def _check_leakage(entity_id: str, properties: dict | object) -> None:
    if not isinstance(properties, dict):
        return
    def _deep(v: object) -> Sequence[str]:
        if isinstance(v, str):
            return [v]
        if isinstance(v, dict):
            return [item for pair in v.items() for item in _deep(pair[0]) + _deep(pair[1])]
        if isinstance(v, (list, tuple, set, frozenset)):
            return [item for item in v for item in _deep(item)]
        return []
    for s in _deep(properties):
        if _LEAKAGE_RE.search(s):
            match = _LEAKAGE_RE.search(s).group().lower()
            raise RequirementInvariantViolation(
                f"Implementation leakage in '{entity_id}': '{match}' is a compiler backend concern"
            )
