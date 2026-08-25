"""v1.2 ISR substrate unit tests — gate-verifiable properties."""

from __future__ import annotations

import ast
import hashlib
import importlib
import json
import os
import pathlib
import random
from collections.abc import Sequence
from typing import Any

import pytest
from pydantic import ValidationError

from isr.adapters.inmemory import ISRImmutableViolation, ISRRevisionNotFound, MemoryISRStore
from isr.core.graph import EDGE_TYPE_COMPATIBILITY, Edge, EdgeType, ISRGraph, Node, NodeType
from isr.core.identity import Provenance, compute_content_hash
from isr.core.invariants import ISRInvariantViolation, validate_invariants
from isr.core.revision import ISRRevision

GENESIS_PROVENANCE = Provenance(
    created_by="genesis",
    created_at="2026-08-26T00:00:00Z",
)

VALID_SCHEMA = "1.0"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _node(nid: str, ntype: NodeType, **props: Any) -> Node:
    return Node(id=nid, type=ntype, properties=props)


def _edge(eid: str, etype: EdgeType, src: str, tgt: str, **props: Any) -> Edge:
    return Edge(id=eid, type=etype, source_id=src, target_id=tgt, properties=props)


def _cap_graph() -> ISRGraph:
    return ISRGraph(
        nodes={
            "svc": _node("svc", NodeType.SERVICE, name="auth-service"),
            "cap": _node("cap", NodeType.CAPABILITY, name="user-auth"),
            "api": _node("api", NodeType.API, path="/auth/login"),
            "db": _node("db", NodeType.DATA_MODEL, name="users"),
            "evt": _node("evt", NodeType.EVENT, name="UserLoggedIn"),
            "pol": _node("pol", NodeType.SECURITY_POLICY, level="strict"),
            "infra": _node("infra", NodeType.INFRASTRUCTURE_TARGET, region="eu-west"),
        },
        edges={
            "impl": _edge("impl", EdgeType.IMPLEMENTED_BY, "cap", "svc"),
            "exp": _edge("exp", EdgeType.EXPOSES, "svc", "api"),
            "per": _edge("per", EdgeType.PERSISTS, "svc", "db"),
            "pub": _edge("pub", EdgeType.PUBLISHES, "svc", "evt"),
            "dep": _edge("dep", EdgeType.DEPENDS_ON, "svc", "svc"),
            "sec": _edge("sec", EdgeType.SECURED_BY, "api", "pol"),
        },
    )


def _simple_graph() -> ISRGraph:
    return ISRGraph(
        nodes={
            "svc": _node("svc", NodeType.SERVICE, name="billing"),
        },
        edges={},
    )


def _make_revision(graph: ISRGraph | None = None, **overrides: Any) -> ISRRevision:
    g = graph or _cap_graph()
    defaults = dict(
        system_id="sys-001",
        revision_id="rev-001",
        schema_version=VALID_SCHEMA,
        graph=g,
        provenance=GENESIS_PROVENANCE,
    )
    defaults.update(overrides)
    return ISRRevision.create(**defaults)


# ---------------------------------------------------------------------------
# G1 — ISR schema is deterministic (roundtrip serialization)
# ---------------------------------------------------------------------------

class TestSchemaDeterminism:
    def test_roundtrip_json(self) -> None:
        rev = _make_revision()
        exported = rev.model_dump(mode="json")
        reimported = ISRRevision.model_validate(exported)
        assert reimported == rev

    def test_roundtrip_dict(self) -> None:
        rev = _make_revision()
        exported = rev.model_dump()
        reimported = ISRRevision.model_validate(exported)
        assert reimported.graph.nodes.keys() == rev.graph.nodes.keys()


# ---------------------------------------------------------------------------
# G2 — graph invariants are enforced
# ---------------------------------------------------------------------------

class TestGraphInvariants:
    def test_valid_graph_passes(self) -> None:
        validate_invariants(_cap_graph())

    def test_dangling_source_raises(self) -> None:
        graph = ISRGraph(
            nodes={"a": _node("a", NodeType.CAPABILITY)},
            edges={"bad": _edge("bad", EdgeType.IMPLEMENTED_BY, "x", "a")},
        )
        with pytest.raises(ISRInvariantViolation, match="missing source"):
            validate_invariants(graph)

    def test_dangling_target_raises(self) -> None:
        graph = ISRGraph(
            nodes={"a": _node("a", NodeType.SERVICE)},
            edges={"bad": _edge("bad", EdgeType.EXPOSES, "a", "x")},
        )
        with pytest.raises(ISRInvariantViolation, match="missing target"):
            validate_invariants(graph)

    def test_type_violation_implemented_by(self) -> None:
        graph = ISRGraph(
            nodes={
                "a": _node("a", NodeType.SERVICE),
                "b": _node("b", NodeType.API),
            },
            edges={"bad": _edge("bad", EdgeType.IMPLEMENTED_BY, "a", "b")},
        )
        with pytest.raises(ISRInvariantViolation, match="source node.*is service"):
            validate_invariants(graph)

    def test_type_violation_secured_by_target(self) -> None:
        graph = ISRGraph(
            nodes={
                "svc": _node("svc", NodeType.SERVICE),
                "api": _node("api", NodeType.API),
            },
            edges={"bad": _edge("bad", EdgeType.SECURED_BY, "svc", "api")},
        )
        with pytest.raises(ISRInvariantViolation, match="target node.*is api"):
            validate_invariants(graph)

    def test_satisfies_requires_requirement_ref_target(self) -> None:
        graph = ISRGraph(
            nodes={
                "cap": _node("cap", NodeType.CAPABILITY),
                "svc": _node("svc", NodeType.SERVICE),
            },
            edges={"bad": _edge("bad", EdgeType.SATISFIES, "cap", "svc")},
        )
        with pytest.raises(ISRInvariantViolation, match="expected.*requirement_ref"):
            validate_invariants(graph)

    def test_requirement_ref_must_carry_ref_id(self) -> None:
        graph = ISRGraph(
            nodes={
                "cap": _node("cap", NodeType.CAPABILITY),
                "rr": _node("rr", NodeType.REQUIREMENT_REF, other="val"),
            },
            edges={"sat": _edge("sat", EdgeType.SATISFIES, "cap", "rr")},
        )
        with pytest.raises(ISRInvariantViolation, match="non-empty string 'ref_id'"):
            validate_invariants(graph)

    def test_requirement_ref_valid(self) -> None:
        graph = ISRGraph(
            nodes={
                "cap": _node("cap", NodeType.CAPABILITY),
                "rr": _node("rr", NodeType.REQUIREMENT_REF, ref_id="REQ-042"),
            },
            edges={"sat": _edge("sat", EdgeType.SATISFIES, "cap", "rr")},
        )
        validate_invariants(graph)


# ---------------------------------------------------------------------------
# G2 — implementation leakage (word-boundary safe)
# ---------------------------------------------------------------------------

class TestLeakageDetection:
    @pytest.mark.parametrize("term", ["postgres", "react", "kubernetes", "docker", "terraform"])
    def test_rejects_forbidden_term(self, term: str) -> None:
        graph = ISRGraph(
            nodes={"a": _node("a", NodeType.SERVICE, tool=term)},
            edges={},
        )
        with pytest.raises(ISRInvariantViolation, match="Implementation leakage"):
            validate_invariants(graph)

    @pytest.mark.parametrize("term", ["postgres", "docker", "react"])
    def test_rejects_in_nested_property(self, term: str) -> None:
        graph = ISRGraph(
            nodes={"a": _node("a", NodeType.SERVICE, details={"runtime": term})},
            edges={},
        )
        with pytest.raises(ISRInvariantViolation, match="Implementation leakage"):
            validate_invariants(graph)

    def test_allows_architecture_primitives(self) -> None:
        graph = ISRGraph(
            nodes={
                "dom": _node("dom", NodeType.DOMAIN, name="payments"),
                "cap": _node("cap", NodeType.CAPABILITY, name="charge-card"),
                "svc": _node("svc", NodeType.SERVICE, name="billing-service"),
            },
            edges={},
        )
        validate_invariants(graph)

    @pytest.mark.parametrize("safe_name", ["lawful-service", "raw-data-node", "flaws-analysis"])
    def test_word_boundary_safe(self, safe_name: str) -> None:
        graph = ISRGraph(
            nodes={"n": _node("n", NodeType.SERVICE, name=safe_name)},
            edges={},
        )
        validate_invariants(graph)

    def test_leakage_in_edge_property(self) -> None:
        graph = ISRGraph(
            nodes={"svc": _node("svc", NodeType.SERVICE)},
            edges={"e": _edge("e", EdgeType.DEPENDS_ON, "svc", "svc", via="kafka")},
        )
        with pytest.raises(ISRInvariantViolation, match="Implementation leakage"):
            validate_invariants(graph)


# ---------------------------------------------------------------------------
# G3 — canonical hashing is deterministic
# ---------------------------------------------------------------------------

class TestHashDeterminism:
    def test_shuffled_insertion_same_hash(self) -> None:
        node_lists = [
            ("a", NodeType.SERVICE, {"z": 1}),
            ("b", NodeType.API, {"m": "hello"}),
            ("c", NodeType.DATA_MODEL, {}),
        ]
        rng1, rng2 = random.Random(42), random.Random(99)
        list1 = list(node_lists)
        list2 = list(node_lists)
        rng1.shuffle(list1)
        rng2.shuffle(list2)

        g1 = ISRGraph(
            nodes={n[0]: Node(id=n[0], type=n[1], properties=n[2]) for n in list1},
            edges={},
        )
        g2 = ISRGraph(
            nodes={n[0]: Node(id=n[0], type=n[1], properties=n[2]) for n in list2},
            edges={},
        )
        assert compute_content_hash(VALID_SCHEMA, g1) == compute_content_hash(VALID_SCHEMA, g2)

    def test_hash_is_stable_json(self) -> None:
        g = _cap_graph()
        h1 = compute_content_hash(VALID_SCHEMA, g)
        h2 = compute_content_hash(VALID_SCHEMA, g)
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex


# ---------------------------------------------------------------------------
# G4 — provenance completeness and revision creation
# ---------------------------------------------------------------------------

class TestProvenanceAndRevision:
    def test_missing_created_by_rejects(self) -> None:
        with pytest.raises(ValidationError, match="created_by"):
            Provenance(created_by="", created_at="2026-08-26T00:00:00Z")

    def test_invalid_isotimestamp_rejects(self) -> None:
        with pytest.raises(ValidationError, match="ISO8601"):
            Provenance(created_by="genesis", created_at="not-a-date")

    def test_invalid_schema_version_rejects(self) -> None:
        with pytest.raises(ValidationError, match="MAJOR.MINOR"):
            _make_revision(schema_version="abc")

    def test_empty_system_id_rejects(self) -> None:
        with pytest.raises(ValidationError, match="system_id"):
            _make_revision(system_id="")

    def test_empty_revision_id_rejects(self) -> None:
        with pytest.raises(ValidationError, match="revision_id"):
            _make_revision(revision_id="")

    def test_content_hash_computed_automatically(self) -> None:
        rev = _make_revision()
        expected = compute_content_hash(VALID_SCHEMA, _cap_graph())
        assert rev.content_hash == expected

    def test_same_graph_same_hash(self) -> None:
        r1 = _make_revision(revision_id="r1")
        r2 = _make_revision(revision_id="r2")
        assert r1.content_hash == r2.content_hash

    def test_different_graph_different_hash(self) -> None:
        g1 = _simple_graph()
        g2 = _cap_graph()
        r1 = _make_revision(graph=g1, revision_id="r1")
        r2 = _make_revision(graph=g2, revision_id="r2")
        assert r1.content_hash != r2.content_hash


# ---------------------------------------------------------------------------
# Immutability — no mutation in place
# ---------------------------------------------------------------------------

class TestImmutability:
    def test_frozen_model_rejects_attribute_assignment(self) -> None:
        rev = _make_revision()
        with pytest.raises(Exception):
            rev.revision_id = "mutated"  # type: ignore[misc]

    def test_graph_copy_yields_new_content_hash(self) -> None:
        rev = _make_revision()
        new_graph = ISRGraph(
            nodes={
                **rev.graph.nodes,
                "new": _node("new", NodeType.EVENT, name="deploy"),
            },
            edges=dict(rev.graph.edges),
        )
        new_rev = _make_revision(graph=new_graph, revision_id="r2")
        assert new_rev.content_hash != rev.content_hash

    def test_original_unchanged(self) -> None:
        rev = _make_revision()
        original_hash = rev.content_hash
        _ = _make_revision(graph=_simple_graph(), revision_id="other")
        assert rev.content_hash == original_hash


# ---------------------------------------------------------------------------
# G5 — storage independence: isr/core + isr/ports must not import tech stacks
# ---------------------------------------------------------------------------

class TestStorageIndependence:
    FORBIDDEN_IMPORTS = frozenset({
        "sqlalchemy",
        "asyncpg",
        "psycopg",
        "psycopg2",
        "neo4j",
        "redis",
        "pymongo",
        "eventstore",
        "kafka",
        "boto3",
        "botocore",
        "google.cloud",
        "azure",
        "aio_pika",
    })

    @pytest.mark.parametrize("package_dir", ["isr/core", "isr/ports"])
    def test_no_forbidden_imports(self, package_dir: str) -> None:
        base = pathlib.Path(package_dir)
        assert base.is_dir(), f"{package_dir} does not exist"
        violations: list[str] = []
        for py_file in base.rglob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if any(alias.name.startswith(fi) for fi in self.FORBIDDEN_IMPORTS):
                            violations.append(f"{py_file}:{node.lineno}: import {alias.name}")
                elif isinstance(node, ast.ImportFrom) and node.module:
                    if any(node.module.startswith(fi) for fi in self.FORBIDDEN_IMPORTS):
                        violations.append(f"{py_file}:{node.lineno}: from {node.module}")
        assert violations == [], f"Forbidden imports found in {package_dir}:\n" + "\n".join(violations)


# ---------------------------------------------------------------------------
# G8 — invalid ISR states rejected at construction (fail-closed)
# ---------------------------------------------------------------------------

class TestFailClosed:
    def test_create_rejects_graph_with_leakage(self) -> None:
        g = ISRGraph(
            nodes={"a": _node("a", NodeType.SERVICE, host="postgres://localhost")},
            edges={},
        )
        with pytest.raises(ISRInvariantViolation):
            _make_revision(graph=g)

    def test_create_rejects_dangling_edge(self) -> None:
        g = ISRGraph(
            nodes={"a": _node("a", NodeType.CAPABILITY)},
            edges={"e": _edge("e", EdgeType.IMPLEMENTED_BY, "a", "missing-svc")},
        )
        with pytest.raises(ISRInvariantViolation):
            _make_revision(graph=g)


# ---------------------------------------------------------------------------
# G6 — exact reconstruction through adapter (in-memory)
# ---------------------------------------------------------------------------

class TestMemoryStoreG6:
    @pytest.mark.asyncio
    async def test_persist_load_roundtrip(self) -> None:
        store = MemoryISRStore()
        rev = _make_revision()
        await store.persist(rev)
        loaded = await store.load(rev.system_id, rev.revision_id)
        assert loaded is not None
        assert loaded.content_hash == rev.content_hash
        assert loaded.model_dump(mode="json") == rev.model_dump(mode="json")

    @pytest.mark.asyncio
    async def test_duplicate_persist_raises_immutability(self) -> None:
        store = MemoryISRStore()
        rev = _make_revision()
        await store.persist(rev)
        with pytest.raises(ISRImmutableViolation):
            await store.persist(rev)

    @pytest.mark.asyncio
    async def test_set_current_not_found_raises(self) -> None:
        store = MemoryISRStore()
        with pytest.raises(ISRRevisionNotFound):
            await store.set_current("sys-001", "nonexistent")

    @pytest.mark.asyncio
    async def test_set_current_and_get(self) -> None:
        store = MemoryISRStore()
        rev = _make_revision()
        await store.persist(rev)
        await store.set_current(rev.system_id, rev.revision_id)
        current = await store.get_current_revision(rev.system_id)
        assert current is not None
        assert current.revision_id == rev.revision_id
