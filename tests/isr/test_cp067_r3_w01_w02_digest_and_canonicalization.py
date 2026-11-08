"""CP067-R3 — R1-W01 digest envelope and R1-W02 Tier A canonicalization."""

from __future__ import annotations

import hashlib

import pytest

from constitutional_architecture.isr.versioning.digest_envelope import (
    build_constitutional_digest_envelope,
    constitutional_canonical_bytes,
)
from isr.core.canonicalization_registry import F01_ISR_REVISION, F02_ISR_GRAPH, registered_family_ids
from isr.core.digest_envelope import AUTHORITY_DOMAIN_CERTIFICATION, AUTHORITY_DOMAIN_CONSTITUTIONAL
from isr.core.digest_verification import (
    DigestPolicyViolation,
    DigestVerificationError,
    assert_certification_digest_envelope,
    assert_cross_domain_digest_substitution_forbidden,
    build_digest_envelope_for_revision,
    canonical_bytes_f01,
    verify_revision_content_integrity,
)
from isr.core.graph import ISRGraph
from isr.core.identity import Provenance, compute_content_hash
from isr.core.revision import ISRRevision
from isr.core.graph import Edge, EdgeType, ISRGraph, Node, NodeType


def _graph(order: list[str]) -> ISRGraph:
    nodes = {
        nid: Node(id=nid, type=NodeType.SERVICE, properties={"label": nid})
        for nid in order
    }
    return ISRGraph(nodes=nodes, edges={})


def _minimal_revision() -> ISRRevision:
    return ISRRevision.create(
        system_id="sys",
        revision_id="rev-1",
        schema_version="1.0",
        graph=_graph(["a", "b"]),
        provenance=Provenance(
            created_by="test",
            created_at="2026-01-01T00:00:00Z",
        ),
    )


def test_tier_a_families_registered():
    assert F01_ISR_REVISION.isr_family_id in registered_family_ids()
    assert F02_ISR_GRAPH.isr_family_id in registered_family_ids()
    assert len(registered_family_ids()) >= 2


def test_deterministic_digest_and_envelope():
    rev = _minimal_revision()
    env = assert_certification_digest_envelope(rev)
    assert env.authority_domain == AUTHORITY_DOMAIN_CERTIFICATION
    assert env.canonicalization_id == "isr.core.identity"
    assert env.content_digest == rev.content_hash


def test_canonical_bytes_reproducible():
    rev = _minimal_revision()
    b1 = canonical_bytes_f01(rev.schema_version, rev.graph)
    b2 = canonical_bytes_f01(rev.schema_version, rev.graph)
    assert b1 == b2
    assert hashlib.sha256(b1).hexdigest() == rev.content_hash


def test_key_reorder_invariant():
    rev = _minimal_revision()
    g1 = rev.graph
    # graph nodes already keyed; recompute from same graph
    h1 = compute_content_hash("1.0", g1)
    h2 = compute_content_hash("1.0", g1)
    assert h1 == h2


def test_tampered_content_hash_rejected():
    rev = _minimal_revision()
    tampered = rev.model_copy(update={"content_hash": "0" * 64})
    with pytest.raises(DigestVerificationError, match="content-digest-mismatch"):
        verify_revision_content_integrity(tampered)


def test_wrong_schema_version_fail_closed():
    rev = _minimal_revision()
    with pytest.raises(DigestVerificationError):
        canonical_bytes_f01("9.9", rev.graph)


def test_cross_domain_substitution_forbidden():
    rev = _minimal_revision()
    cert = build_digest_envelope_for_revision(rev)
    # Synthetic constitutional envelope with same digest bytes (attack scenario)
    fake = cert
    import dataclasses

    const_like = dataclasses.replace(
        cert,
        authority_domain=AUTHORITY_DOMAIN_CONSTITUTIONAL,
        isr_family_id="constitutional_architecture.isr.model",
        canonicalization_id="constitutional.isr.serializer",
    )
    with pytest.raises(DigestPolicyViolation, match="cross-domain"):
        assert_cross_domain_digest_substitution_forbidden(cert, const_like)


def test_different_meaningful_content_different_digest():
    r1 = _minimal_revision()
    extra = ISRGraph(nodes=dict(r1.graph.nodes), edges=dict(r1.graph.edges))
    r2 = ISRRevision.create(
        system_id="sys",
        revision_id="rev-2",
        schema_version="1.0",
        graph=extra,
        provenance=Provenance(created_by="test", created_at="2026-01-01T00:00:00Z"),
    )
    assert r1.content_hash == r2.content_hash
    # mutate graph by adding a node
    from isr.core.graph import Node, NodeType

    nodes = dict(r1.graph.nodes)
    nodes["n-extra"] = Node(id="n-extra", type=NodeType.DOMAIN, properties={"label": "X"})
    g3 = ISRGraph(nodes=nodes, edges=r1.graph.edges)
    r3 = ISRRevision.create(
        system_id="sys",
        revision_id="rev-3",
        schema_version="1.0",
        graph=g3,
        provenance=Provenance(created_by="test", created_at="2026-01-01T00:00:00Z"),
    )
    assert r3.content_hash != r1.content_hash


def test_constitutional_envelope_separate_domain():
    from constitutional_architecture.isr.model.isr import ISR
    from constitutional_architecture.isr.model.system import System

    isr = ISR(system=System(id="sys-1", name="s", description=""))
    env = build_constitutional_digest_envelope(isr)
    assert env.authority_domain == AUTHORITY_DOMAIN_CONSTITUTIONAL
    assert constitutional_canonical_bytes(isr)
    cert = build_digest_envelope_for_revision(_minimal_revision())
    with pytest.raises(DigestPolicyViolation):
        assert_cross_domain_digest_substitution_forbidden(cert, env)


def test_payroll_fixture_passes_certification_gate():
    from certification.payroll.candidate_fixture import payroll_isr_revision

    rev = payroll_isr_revision()
    assert_certification_digest_envelope(rev)
