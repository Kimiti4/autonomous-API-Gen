"""Controlled TOR extraction preserves provenance and requires explicit review."""
from __future__ import annotations

import pytest

from isr.core.graph import NodeType
from reqgraph.core.graph import Priority, RequirementKind
from reqgraph.core.tor_extraction import (
    RequirementReview,
    extract_tor,
    map_reviewed_tor_to_isr,
    reviewed_requirements_to_graph,
)


TOR = """# Payroll Software
## Objectives
The software shall calculate salary and generate payslips.
## Security
The system must enforce role-based access controls.
## Background
World Concern serves communities in several countries.
## Employee Self Service
- Employees should be able to view payslips.
- Update personal information subject to approval.
"""


def test_extraction_is_deterministic_and_source_bound():
    first = extract_tor(TOR, "world-concern-payroll-tor")
    second = extract_tor(TOR, "world-concern-payroll-tor")
    assert first.source_sha256 == second.source_sha256
    assert [candidate.candidate_id for candidate in first.candidates] == [
        candidate.candidate_id for candidate in second.candidates
    ]
    assert all(candidate.review_status == "pending_review" for candidate in first.candidates)
    assert all(candidate.source_sha256 == first.source_sha256 for candidate in first.candidates)
    assert any(item["reason"] == "context-not-explicit-obligation" for item in first.ignored_context)


def test_unclassified_list_items_are_preserved_as_review_candidates():
    extraction = extract_tor(TOR, "world-concern-payroll-tor")
    assert any(candidate.statement.startswith("Update personal information") for candidate in extraction.candidates)
    candidate = next(candidate for candidate in extraction.candidates if candidate.statement.startswith("Update personal information"))
    assert candidate.candidate_kind is None
    assert candidate.ambiguity_score > 0.5
    assert candidate.review_status == "pending_review"


def test_only_explicitly_reviewed_candidates_enter_requirement_graph():
    extraction = extract_tor(TOR, "world-concern-payroll-tor")
    functional = next(candidate for candidate in extraction.candidates if "calculate salary" in candidate.statement)
    with pytest.raises(ValueError, match="requires an explicit reviewer"):
        reviewed_requirements_to_graph(extraction, {
            functional.candidate_id: RequirementReview(
                candidate_id=functional.candidate_id,
                kind=RequirementKind.FUNCTIONAL,
                priority=Priority.MUST,
                acceptance_criteria=("gross pay equals base salary plus declared allowances",),
            )
        })

    with pytest.raises(ValueError, match="needs acceptance criteria"):
        reviewed_requirements_to_graph(extraction, {
            functional.candidate_id: RequirementReview(
                candidate_id=functional.candidate_id,
                kind=RequirementKind.FUNCTIONAL,
                priority=Priority.MUST,
                acceptance_criteria=(),
                approved_by="authorized-reviewer",
            )
        })


def test_approved_requirement_maps_through_genesis_into_canonical_isr():
    extraction = extract_tor(TOR, "world-concern-payroll-tor")
    functional = next(candidate for candidate in extraction.candidates if "calculate salary" in candidate.statement)
    security = next(candidate for candidate in extraction.candidates if "role-based access controls" in candidate.statement)
    reviews = {
        functional.candidate_id: RequirementReview(
            candidate_id=functional.candidate_id,
            kind=RequirementKind.FUNCTIONAL,
            priority=Priority.MUST,
            acceptance_criteria=("gross pay equals base salary plus declared allowances",),
            approved_by="authorized-reviewer",
        ),
        security.candidate_id: RequirementReview(
            candidate_id=security.candidate_id,
            kind=RequirementKind.CONSTRAINT,
            priority=Priority.MUST,
            acceptance_criteria=("unauthorized payroll actions are denied",),
            approved_by="authorized-reviewer",
        ),
    }
    mapped = map_reviewed_tor_to_isr(
        extraction,
        reviews,
        system_id="world-concern-payroll",
        revision_id="tor-rev-1",
        created_at="2026-10-19T10:00:00Z",
    )
    assert set(mapped.requirement_graph.nodes) == {functional.candidate_id, security.candidate_id}
    refs = [
        node for node in mapped.revision.graph.nodes.values()
        if node.type == NodeType.REQUIREMENT_REF
    ]
    assert {node.properties["ref_id"] for node in refs} == set(mapped.requirement_graph.nodes)
    assert set(mapped.revision.provenance.requirement_refs) == set(mapped.requirement_graph.nodes)
    assert all(node.properties["source_text_sha256"] == extraction.source_sha256 for node in mapped.requirement_graph.nodes.values())


def test_ambiguous_candidate_requires_resolution_reference():
    extraction = extract_tor(TOR, "world-concern-payroll-tor")
    candidate = next(candidate for candidate in extraction.candidates if candidate.statement.startswith("Update personal information"))
    with pytest.raises(ValueError, match="needs a resolution reference"):
        reviewed_requirements_to_graph(extraction, {
            candidate.candidate_id: RequirementReview(
                candidate_id=candidate.candidate_id,
                kind=RequirementKind.FUNCTIONAL,
                priority=Priority.SHOULD,
                acceptance_criteria=("updated personal details appear only after approval",),
                ambiguity_score=0.8,
                approved_by="authorized-reviewer",
            )
        })
