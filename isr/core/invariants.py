"""Constitutional invariant enforcement — fail-closed at construction."""

from __future__ import annotations

import re
from itertools import chain
from typing import Sequence

from isr.core.graph import EDGE_TYPE_COMPATIBILITY, Edge, EdgeType, ISRGraph, Node, NodeType


class ISRInvariantViolation(Exception):
    """Raised when an ISR graph violates a constitutional invariant."""


FORBIDDEN_IMPLEMENTATION_TERMS: Sequence[str] = (
    "aws",
    "boto",
    "docker",
    "django",
    "fastapi",
    "flask",
    "graphql",
    "grpc",
    "java",
    "kafka",
    "kubernetes",
    "mongo",
    "mysql",
    "nestjs",
    "neo4j",
    "nginx",
    "nodejs",
    "postgres",
    "postgresql",
    "rabbitmq",
    "react",
    "redis",
    "spring",
    "terraform",
    "vue",
)

_LEAKAGE_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(t) for t in FORBIDDEN_IMPLEMENTATION_TERMS) + r")\b",
    re.IGNORECASE,
)


def validate_invariants(graph: ISRGraph) -> None:
    """Enforces constitutional invariants on the ISR graph.  Raises on the
    first violation encountered (fail-closed)."""

    node_ids = set(graph.nodes.keys())

    # 1. No orphan node/edge ids  (edge id uniqueness is structural)
    if len(graph.edges) != len({e.id for e in graph.edges.values()}):
        dupes = [eid for eid, e in graph.edges.items()
                 if sum(1 for ee in graph.edges.values() if ee.id == eid) > 1]
        raise ISRInvariantViolation(f"Duplicate edge ids: {dupes[:5]}")

    # 2. Referential integrity + type validity + leakage
    for edge in graph.edges.values():
        if edge.source_id not in node_ids:
            raise ISRInvariantViolation(
                f"Edge '{edge.id}' references missing source node '{edge.source_id}'"
            )
        if edge.target_id not in node_ids:
            raise ISRInvariantViolation(
                f"Edge '{edge.id}' references missing target node '{edge.target_id}'"
            )

        src_type = graph.nodes[edge.source_id].type
        tgt_type = graph.nodes[edge.target_id].type

        compat = EDGE_TYPE_COMPATIBILITY.get(edge.type)
        if compat is not None:
            src_allowed, tgt_allowed = compat
            if src_type not in src_allowed:
                raise ISRInvariantViolation(
                    f"Edge '{edge.id}' type '{edge.type.value}': "
                    f"source node '{edge.source_id}' is {src_type.value} "
                    f"(expected {sorted(s.value for s in src_allowed)})"
                )
            if tgt_type not in tgt_allowed:
                raise ISRInvariantViolation(
                    f"Edge '{edge.id}' type '{edge.type.value}': "
                    f"target node '{edge.target_id}' is {tgt_type.value} "
                    f"(expected {sorted(t.value for t in tgt_allowed)})"
                )

        _check_leakage(f"edge:{edge.id}", chain(
            _mapping_strings(edge.properties),
            [edge.type.value],
        ))

    # 3. Requirement-ref nodes must carry a ref_id
    for node in graph.nodes.values():
        if node.type == NodeType.REQUIREMENT_REF:
            ref_id = node.properties.get("ref_id")
            if not isinstance(ref_id, str) or not ref_id.strip():
                raise ISRInvariantViolation(
                    f"Requirement-ref node '{node.id}' must carry a non-empty "
                    f"string 'ref_id' in its properties"
                )
        _check_leakage(
            f"node:{node.id}",
            chain(_mapping_strings(node.properties), [node.type.value]),
        )

    # 4. Determinism seed: sorted-node schema is stable; invariants assume
    #    sorted iteration for deterministic error messages (addresses G1/G3).


def _mapping_strings(properties: dict | object) -> Sequence[str]:
    """Yield every string value (and key) nested in a properties mapping."""
    if not isinstance(properties, dict):
        return []
    def _deep(v: object) -> Sequence[str]:
        if isinstance(v, str):
            return [v]
        if isinstance(v, dict):
            return chain.from_iterable(_deep(val) for pair in v.items() for val in pair)
        if isinstance(v, (list, tuple, set, frozenset)):
            return chain.from_iterable(_deep(item) for item in v)
        return []
    return list(chain.from_iterable(_deep(val) for pair in properties.items() for val in pair))


def _check_leakage(entity_id: str, strings: Sequence[str]) -> None:
    for s in strings:
        if _LEAKAGE_RE.search(s):
            match = _LEAKAGE_RE.search(s).group().lower()
            raise ISRInvariantViolation(
                f"Implementation leakage in '{entity_id}': "
                f"'{match}' is a compiler backend concern, not an ISR primitive"
            )
