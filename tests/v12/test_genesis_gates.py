"""v1.2 Genesis gates G10, G11 — genesis mapping and evidence certification."""

from __future__ import annotations

import pytest

from isr.core.identity import Provenance, compute_content_hash
from isr.core.invariants import ISRInvariantViolation, validate_invariants
from isr.core.revision import ISRRevision
from genesis.evidence import (
    ConsistencyReport,
    CoverageReport,
    GenesisEvidence,
    ValidationRecord,
    project_to_v11_evidence,
)
from genesis.mapper import ReferenceDeterministicMapper
from genesis.validator import ReferenceGenesisValidator
from reqgraph.core.graph import (
    Priority,
    RequirementEdge,
    RequirementEdgeType,
    RequirementGraph,
    RequirementKind,
    RequirementNode,
)
from reqgraph.core.invariants import RequirementInvariantViolation, validate_requirement_graph


def _simple_req() -> RequirementGraph:
    n = RequirementNode(
        id="r1",
        kind=RequirementKind.FUNCTIONAL,
        statement="do x",
        priority=Priority.MUST,
        acceptance_criteria=["ac1"],
    )
    return RequirementGraph(schema_version="1.0", nodes={"r1": n}, edges={})


def _multi_req() -> RequirementGraph:
    nodes = {
        "r1": RequirementNode(
            id="r1",
            kind=RequirementKind.FUNCTIONAL,
            statement="authenticate users",
            priority=Priority.MUST,
            acceptance_criteria=["login succeeds"],
        ),
        "r2": RequirementNode(
            id="r2",
            kind=RequirementKind.DOMAIN_CONCEPT,
            statement="user identity domain",
            priority=Priority.SHOULD,
        ),
        "r3": RequirementNode(
            id="r3",
            kind=RequirementKind.NON_FUNCTIONAL,
            statement="sub-100ms latency",
            priority=Priority.MUST,
        ),
    }
    edges = {
        "e1": RequirementEdge(
            id="e1",
            type=RequirementEdgeType.DEPENDS_ON,
            source_id="r1",
            target_id="r2",
        ),
    }
    return RequirementGraph(schema_version="1.0", nodes=nodes, edges=edges)


# ---------------------------------------------------------------------------
# G10 — Genesis produces valid ISR₀
# ---------------------------------------------------------------------------

def test_g10_genesis_deterministic() -> None:
    m = ReferenceDeterministicMapper()
    r1 = m.map(_simple_req(), "map-1.0")
    r2 = m.map(_simple_req(), "map-1.0")
    assert compute_content_hash("1.0", r1.graph) == compute_content_hash("1.0", r2.graph)


def test_g10_genesis_passes_adr008_invariants() -> None:
    m = ReferenceDeterministicMapper()
    result = m.map(_simple_req(), "map-1.0")
    validate_invariants(result.graph)


def test_g10_genesis_creates_valid_revision() -> None:
    m = ReferenceDeterministicMapper()
    result = m.map(_simple_req(), "map-1.0")
    rev = ISRRevision.create(
        "sys",
        "rev0",
        "1.0",
        result.graph,
        Provenance(created_by="genesis", created_at="2026-01-01T00:00:00Z"),
    )
    assert len(rev.content_hash) == 64


def test_g10_coverage_complete() -> None:
    m = ReferenceDeterministicMapper()
    result = m.map(_simple_req(), "map-1.0")
    assert not result.coverage.uncovered
    assert "r1" in result.coverage.requirement_to_isr


def test_g10_multi_requirement_coverage() -> None:
    m = ReferenceDeterministicMapper()
    result = m.map(_multi_req(), "map-1.0")
    assert not result.coverage.uncovered
    assert len(result.coverage.requirement_to_isr) == 3


def test_g10_constitutional_defaults_injected() -> None:
    m = ReferenceDeterministicMapper()
    result = m.map(_simple_req(), "map-1.0")
    default_nodes = [
        nid for nid in result.graph.nodes
        if "constitution" in nid
    ]
    assert len(default_nodes) == 5


def test_g10_stakeholders_not_mapped() -> None:
    """Stakeholder nodes are problem-space-only; they produce no ISR nodes."""
    req = RequirementGraph(
        schema_version="1.0",
        nodes={
            "r1": RequirementNode(
                id="r1",
                kind=RequirementKind.STAKEHOLDER,
                statement="the product owner",
                priority=Priority.MUST,
            ),
        },
        edges={},
    )
    m = ReferenceDeterministicMapper()
    result = m.map(req, "map-1.0")
    # Stakeholders are skipped; only constitutional defaults exist
    assert len(result.graph.nodes) == 5


# ---------------------------------------------------------------------------
# G11 — Genesis evidence is certifiable by v1.1 accountability plane
# ---------------------------------------------------------------------------

def _make_genesis_evidence(
    isr_hash: str = "abc123",
    req_hash: str = "def456",
) -> GenesisEvidence:
    return GenesisEvidence(
        genesis_id="g1",
        mapping_spec_version="map-1.0",
        requirement_graph_hash=req_hash,
        isr_candidate_hash=isr_hash,
        coverage=CoverageReport(
            requirement_to_isr={"r1": ["capability:r1"]},
            uncovered=[],
        ),
        consistency=ConsistencyReport(
            ambiguities_resolved=0,
            conflicts_resolved=0,
        ),
        validation=ValidationRecord(
            adr008_invariants_passed=True,
            content_hash=isr_hash,
        ),
        created_by="genesis",
        created_at="2026-01-01T00:00:00Z",
    )


def test_g11_genesis_evidence_types() -> None:
    ev = _make_genesis_evidence()
    recs = project_to_v11_evidence(ev)
    assert {r.evidenceType for r in recs} == {
        "genesis-coverage",
        "genesis-consistency",
        "genesis-validation",
    }


def test_g11_genesis_evidence_content_hash_present() -> None:
    ev = _make_genesis_evidence()
    recs = project_to_v11_evidence(ev)
    assert all(r.contentHash for r in recs)
    assert all(len(r.contentHash) == 64 for r in recs)


def test_g11_genesis_evidence_subject_ref() -> None:
    ev = _make_genesis_evidence(isr_hash="xyz")
    recs = project_to_v11_evidence(ev)
    assert all(r.subjectRef == "xyz" for r in recs)


def test_g11_validator_passes_on_valid() -> None:
    m = ReferenceDeterministicMapper()
    result = m.map(_simple_req(), "map-1.0")
    rev = ISRRevision.create(
        "sys", "rev0", "1.0", result.graph,
        Provenance(created_by="genesis", created_at="2026-01-01T00:00:00Z"),
    )
    ev = GenesisEvidence(
        genesis_id="g1",
        mapping_spec_version="map-1.0",
        requirement_graph_hash="req_hash",
        isr_candidate_hash=rev.content_hash,
        coverage=CoverageReport(
            requirement_to_isr={"r1": ["capability:r1"]},
            uncovered=[],
        ),
        consistency=ConsistencyReport(),
        validation=ValidationRecord(
            adr008_invariants_passed=True,
            content_hash=rev.content_hash,
        ),
        created_by="genesis",
        created_at="2026-01-01T00:00:00Z",
    )
    validator = ReferenceGenesisValidator()
    violations = validator.validate(rev, ev)
    assert violations == []


def test_g11_validator_catches_hash_mismatch() -> None:
    m = ReferenceDeterministicMapper()
    result = m.map(_simple_req(), "map-1.0")
    rev = ISRRevision.create(
        "sys", "rev0", "1.0", result.graph,
        Provenance(created_by="genesis", created_at="2026-01-01T00:00:00Z"),
    )
    ev = GenesisEvidence(
        genesis_id="g1",
        mapping_spec_version="map-1.0",
        requirement_graph_hash="req_hash",
        isr_candidate_hash=rev.content_hash,
        coverage=CoverageReport(requirement_to_isr={"r1": ["capability:r1"]}),
        consistency=ConsistencyReport(),
        validation=ValidationRecord(
            adr008_invariants_passed=True,
            content_hash="WRONG_HASH",
        ),
        created_by="genesis",
        created_at="2026-01-01T00:00:00Z",
    )
    validator = ReferenceGenesisValidator()
    violations = validator.validate(rev, ev)
    assert len(violations) > 0
    assert "content_hash mismatch" in violations[0]


# ---------------------------------------------------------------------------
# Requirement Graph invariants (pre-genesis validation)
# ---------------------------------------------------------------------------

def test_reqgraph_rejects_unresolved_conflict() -> None:
    req = RequirementGraph(
        schema_version="1.0",
        nodes={
            "r1": RequirementNode(
                id="r1",
                kind=RequirementKind.FUNCTIONAL,
                statement="fast",
                priority=Priority.MUST,
                acceptance_criteria=["ac"],
            ),
            "r2": RequirementNode(
                id="r2",
                kind=RequirementKind.FUNCTIONAL,
                statement="thorough",
                priority=Priority.MUST,
                acceptance_criteria=["ac"],
            ),
        },
        edges={
            "c1": RequirementEdge(
                id="c1",
                type=RequirementEdgeType.CONFLICTS_WITH,
                source_id="r1",
                target_id="r2",
            ),
        },
    )
    with pytest.raises(RequirementInvariantViolation, match="unresolved"):
        validate_requirement_graph(req)


def test_reqgraph_rejects_functional_without_criteria() -> None:
    req = RequirementGraph(
        schema_version="1.0",
        nodes={
            "r1": RequirementNode(
                id="r1",
                kind=RequirementKind.FUNCTIONAL,
                statement="do thing",
                priority=Priority.MUST,
                acceptance_criteria=[],
            ),
        },
        edges={},
    )
    with pytest.raises(RequirementInvariantViolation, match="acceptance criteria"):
        validate_requirement_graph(req)


def test_reqgraph_rejects_high_ambiguity_without_resolution() -> None:
    req = RequirementGraph(
        schema_version="1.0",
        nodes={
            "r1": RequirementNode(
                id="r1",
                kind=RequirementKind.NON_FUNCTIONAL,
                statement="should be fast",
                priority=Priority.SHOULD,
                ambiguity_score=0.8,
                resolution_ref=None,
            ),
        },
        edges={},
    )
    with pytest.raises(RequirementInvariantViolation, match="ambiguity"):
        validate_requirement_graph(req)
