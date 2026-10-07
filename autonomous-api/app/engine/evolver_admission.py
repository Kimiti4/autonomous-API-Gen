"""Governed acceptance boundary for domain evolution proposals.

This is intentionally an adapter/gate: it does not authorize deployment or mutate
the running system. The existing EvolutionEngine remains responsible for search,
evaluation, lineage and build lifecycle.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from app.engine.evolver_bridge import EvolverProposal, proposal_ready_for_evolver
from app.engine.evolution_selection import CandidateAssessment, assess_candidate


@dataclass(frozen=True)
class EvolverAdmission:
    admitted: bool
    proposal_id: str
    reasons: tuple[str, ...]
    metadata: dict[str, Any]


def admit_proposal(
    proposal: EvolverProposal,
    *,
    required_domains: tuple[str, ...] = (),
    required_properties: tuple[str, ...] = (),
) -> EvolverAdmission:
    reasons: list[str] = []

    if not proposal_ready_for_evolver(proposal):
        reasons.append("proposal-not-ready")

    if required_domains:
        missing = sorted(set(required_domains) - set(proposal.domains))
        if missing:
            reasons.append("missing-domains:" + ",".join(missing))

    if required_properties:
        missing = sorted(set(required_properties) - set(proposal.expected_properties))
        if missing:
            reasons.append("missing-properties:" + ",".join(missing))

    return EvolverAdmission(
        admitted=not reasons,
        proposal_id=proposal.proposal_id,
        reasons=tuple(reasons),
        metadata={
            "domains": proposal.domains,
            "candidate_ids": proposal.candidate_ids,
            "evidence_count": len(proposal.evidence),
            "expected_properties": proposal.expected_properties,
        },
    )


def admission_to_evolution_context(
    admission: EvolverAdmission,
) -> dict[str, Any]:
    """Create immutable-style context for an evolution run.

    No implementation, deployment, or authorization capability is exposed.
    """
    if not admission.admitted:
        raise ValueError("cannot create evolution context from rejected proposal")
    return {
        "proposal_id": admission.proposal_id,
        "candidate_ids": admission.metadata["candidate_ids"],
        "domains": admission.metadata["domains"],
        "expected_properties": admission.metadata["expected_properties"],
        "evidence_count": admission.metadata["evidence_count"],
    }


# Compatibility export: the assessment function remains part of the governed
# admission surface while its canonical implementation lives in evolution_selection.
