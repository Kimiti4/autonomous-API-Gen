"""Adapter from domain evolution candidates into the existing evolution pipeline."""
from __future__ import annotations
from dataclasses import dataclass
from .evolution_domains import EngineeringCandidate
from .evolution_selection import EvolutionOption


@dataclass(frozen=True)
class EvolverProposal:
    proposal_id: str
    candidate_ids: tuple[str, ...]
    domains: tuple[str, ...]
    hypotheses: tuple[str, ...]
    changes: tuple[str, ...]
    expected_properties: tuple[str, ...]
    evidence: tuple[str, ...]
    risk_flags: tuple[str, ...]


def to_evolver_proposal(
    option: EvolutionOption,
    candidates: tuple[EngineeringCandidate, ...],
) -> EvolverProposal:
    selected = {
        c.candidate_id: c for c in candidates
        if c.candidate_id in option.candidate_ids
    }
    ordered = [selected[i] for i in option.candidate_ids if i in selected]
    return EvolverProposal(
        proposal_id=option.option_id,
        candidate_ids=option.candidate_ids,
        domains=option.domains,
        hypotheses=tuple(c.hypothesis for c in ordered),
        changes=tuple(sorted({x for c in ordered for x in c.changes})),
        expected_properties=option.covered_properties,
        evidence=option.evidence,
        risk_flags=option.risks,
    )


def proposal_ready_for_evolver(
    proposal: EvolverProposal,
) -> bool:
    return (
        bool(proposal.candidate_ids)
        and bool(proposal.evidence)
        and not proposal.risk_flags
        and bool(proposal.expected_properties)
    )
