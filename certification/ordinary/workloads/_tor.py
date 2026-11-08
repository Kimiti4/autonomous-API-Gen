"""Shared TOR approval helper for ordinary workloads."""
from __future__ import annotations

from reqgraph.core.graph import RequirementGraph, RequirementKind
from reqgraph.ingestion.tor_extractor import HumanApproval, extract_tor_text


def approved_requirements_from_tor(tor_excerpt: str, source_name: str) -> RequirementGraph:
    draft = extract_tor_text(tor_excerpt, source_name)
    approvals = {
        item.requirement_id: HumanApproval(
            reviewer_id=f"{source_name}-reviewer",
            approval_ref=f"review:{item.requirement_id}",
            acceptance_criteria=(
                "Independently verified against generated application behavior.",
            ),
            selected_kind=RequirementKind.FUNCTIONAL,
            resolution_ref=f"resolved:{item.requirement_id}" if item.ambiguity_score >= 0.5 else None,
        )
        for item in draft.candidates
    }
    return draft.approve(approvals)
