"""v1.2 ISR gates G1–G4, G8, G9 — schema, invariants, hashing, provenance."""

from __future__ import annotations

import pytest

from isr.core.graph import Edge, EdgeType, ISRGraph, Node, NodeType
from isr.core.identity import Provenance, compute_content_hash
from isr.core.invariants import ISRInvariantViolation, validate_invariants
from isr.core.revision import ISRRevision
from isr.schema.versions import migrate_1_0_to_1_1


def _graph(order: list[str]) -> ISRGraph:
    nodes = {
        nid: Node(id=nid, type=NodeType.SERVICE, properties={"label": nid})
        for nid in order
    }
    return ISRGraph(nodes=nodes, edges={})


def test_g1_schema_determinism() -> None:
    g = _graph(["a", "b"])
    roundtrip = ISRGraph.model_validate_json(g.model_dump_json())
    assert roundtrip == g


def test_g2_invariants_dangling_edge() -> None:
    g = ISRGraph(
        nodes={"a": Node(id="a", type=NodeType.SERVICE)},
        edges={
            "e": Edge(
                id="e",
                type=EdgeType.DEPENDS_ON,
                source_id="a",
                target_id="missing",
            )
        },
    )
    with pytest.raises(ISRInvariantViolation):
        validate_invariants(g)


def test_g2_invariants_leakage() -> None:
    g = ISRGraph(
        nodes={
            "a": Node(
                id="a",
                type=NodeType.SERVICE,
                properties={"db": "postgres"},
            )
        },
        edges={},
    )
    with pytest.raises(ISRInvariantViolation):
        validate_invariants(g)


def test_g3_hash_determinism() -> None:
    g1 = _graph(["a", "b"])
    g2 = _graph(["b", "a"])
    assert compute_content_hash("1.0", g1) == compute_content_hash("1.0", g2)


def test_g4_provenance_missing_created_by() -> None:
    with pytest.raises(Exception):
        Provenance(created_at="2026-01-01T00:00:00Z")


def test_g8_invalid_rejection() -> None:
    bad = ISRGraph(
        nodes={
            "a": Node(
                id="a",
                type=NodeType.SERVICE,
                properties={"x": "kubernetes"},
            )
        },
        edges={},
    )
    with pytest.raises(ISRInvariantViolation):
        ISRRevision.create(
            "sys",
            "rev1",
            "1.0",
            bad,
            Provenance(created_by="test", created_at="2026-01-01T00:00:00Z"),
        )


def test_g9_schema_evolution_deterministic() -> None:
    g = _graph(["a"])
    m1 = migrate_1_0_to_1_1(g)
    m2 = migrate_1_0_to_1_1(g)
    assert compute_content_hash("1.1", m1) == compute_content_hash("1.1", m2)


def test_g9_schema_evolution_adds_version_property() -> None:
    g = _graph(["a"])
    migrated = migrate_1_0_to_1_1(g)
    assert migrated.nodes["a"].properties["schema_version"] == "1.1"
    assert "schema_version" not in g.nodes["a"].properties
