"""Controlled TOR extraction and requirement-to-ISR projection tests."""
from __future__ import annotations

import pytest

from isr.core.graph import ISRGraph, Node, NodeType
from reqgraph.adapters.isr_projection import merge_requirement_projection, project_requirement_graph
from reqgraph.core.graph import RequirementKind
from reqgraph.ingestion.tor_extractor import (
    HumanApproval,
    ReviewStatus,
    extract_tor_text,
)


TOR = """2. OBJECTIVES
The payroll system shall:
- Automate payroll calculations and processing.
- Ensure compliance with applicable tax laws and statutory deductions.
3. TECHNICAL REQUIREMENTS
The software should:
- Be web-based and support mobile access where applicable.
- Include role-based access controls and audit trail functionality.
"""


def test_tor_extraction_is_deterministic_and_keeps_candidates_unapproved():
    first = extract_tor_text(TOR, "world-concern-tor.txt")
    second = extract_tor_text(TOR, "world-concern-tor.txt")
    assert first.source_sha256 == second.source_sha256
    assert first.source_text == TOR
    assert [item.requirement_id for item in first.candidates] == [
        item.requirement_id for item in second.candidates
    ]
    assert all(item.status is ReviewStatus.NEEDS_REVIEW for item in first.candidates)
    assert all(item.source_ref.startswith("world-concern-tor.txt#L") for item in first.candidates)
    assert any("Automate payroll calculations" in item.statement for item in first.candidates)
    assert any(item.proposed_kind is RequirementKind.NON_FUNCTIONAL for item in first.candidates)


def test_source_mutation_invalidates_approval():
    draft = extract_tor_text(TOR, "world-concern-tor.txt")
    mutated = draft.model_copy(update={"source_text": TOR + "\\nchanged"})
    approvals = {
        candidate.requirement_id: HumanApproval(
            reviewer_id="reviewer",
            approval_ref=f"decision:{candidate.requirement_id}",
            acceptance_criteria=("An independently authored test verifies this requirement.",),
        )
        for candidate in draft.candidates
    }
    with pytest.raises(ValueError, match="source changed"):
        mutated.approve(approvals)


def test_tor_candidates_cannot_be_promoted_without_human_approval():
    draft = extract_tor_text(TOR, "world-concern-tor.txt")
    with pytest.raises(ValueError, match="approval set must match"):
        draft.approve({})


def test_approved_tor_becomes_requirement_graph_and_then_isr_refs_only():
    draft = extract_tor_text(
        "TECHNICAL REQUIREMENTS\n- The system shall support payroll run creation.",
        "payroll-tor.txt",
    )
    approvals = {
        candidate.requirement_id: HumanApproval(
            reviewer_id="human-reviewer",
            approval_ref=f"decision:{candidate.requirement_id}",
            acceptance_criteria=("A payroll run can be created and retrieved in an integration test.",),
        )
        for candidate in draft.candidates
    }
    graph = draft.approve(approvals)
    projected = project_requirement_graph(graph)
    assert len(projected.nodes) == len(graph.nodes)
    assert all(node.type is NodeType.REQUIREMENT_REF for node in projected.nodes.values())
    assert all(node.properties["review_status"] == "approved" for node in projected.nodes.values())
    assert not projected.edges

    base = ISRGraph(nodes={
        "service:payroll": Node(id="service:payroll", type=NodeType.SERVICE, properties={"label": "Payroll"}),
    })
    merged = merge_requirement_projection(base, graph)
    assert "service:payroll" in merged.nodes
    assert any(node.type is NodeType.REQUIREMENT_REF for node in merged.nodes.values())


def test_ambiguous_candidate_requires_recorded_resolution_before_graph_creation():
    draft = extract_tor_text(
        "TECHNICAL REQUIREMENTS\n- The system shall provide appropriate and reasonable payroll support where possible.",
        "ambiguous-tor.txt",
    )
    candidate = draft.candidates[0]
    assert candidate.ambiguity_score > 0.5
    approval = HumanApproval(
        reviewer_id="reviewer",
        approval_ref="decision:ambiguous",
        acceptance_criteria=("The reviewer confirms the supported payroll workflows in a signed test checklist.",),
    )
    with pytest.raises(ValueError, match="ambiguity resolution"):
        draft.approve({candidate.requirement_id: approval})


def test_path_and_content_changes_produce_distinct_candidate_ids():
    first = extract_tor_text("TECHNICAL REQUIREMENTS\n- The system shall support payroll.", "a.txt")
    changed = extract_tor_text("TECHNICAL REQUIREMENTS\n- The system shall support leave.", "a.txt")
    assert first.source_sha256 != changed.source_sha256
    assert first.candidates[0].requirement_id != changed.candidates[0].requirement_id
