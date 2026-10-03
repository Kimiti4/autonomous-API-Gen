"""Evidence-preserving synthesis of competing domain proposals."""
from __future__ import annotations
from dataclasses import dataclass
from .domain_proposals import DomainProposal, DomainRebuttal, validate_proposal, validate_rebuttal


@dataclass(frozen=True)
class SynthesizedProposal:
    proposal_id: str
    problem_signature: str
    source_proposal_ids: tuple[str, ...]
    source_rebuttal_ids: tuple[str, ...]
    domains: tuple[str, ...]
    claim: str
    changes: tuple[str, ...]
    target_properties: tuple[str, ...]
    evidence: tuple[str, ...]
    unresolved_concerns: tuple[str, ...]


def synthesize(
    proposal_id: str,
    proposals: tuple[DomainProposal, ...],
    rebuttals: tuple[DomainRebuttal, ...],
) -> SynthesizedProposal:
    if not proposals:
        raise ValueError("synthesis-requires-proposals")

    valid = [p for p in proposals if validate_proposal(p).accepted_for_evaluation]
    if not valid:
        raise ValueError("no-valid-proposals")

    invalid_rebuttals = [
        r for r in rebuttals if validate_rebuttal(r)
    ]
    if invalid_rebuttals:
        raise ValueError("invalid-rebuttal-in-synthesis")

    problem = valid[0].problem_signature
    if any(p.problem_signature != problem for p in valid):
        raise ValueError("proposal-problem-mismatch")

    changes = tuple(sorted({x for p in valid for x in p.changes}))
    properties = tuple(sorted({x for p in valid for x in p.target_properties}))
    evidence = tuple(sorted({x for p in valid for x in p.evidence} |
                            {x for r in rebuttals for x in r.evidence}))
    concerns = tuple(sorted({x for r in rebuttals for x in r.concerns}))

    return SynthesizedProposal(
        proposal_id,
        problem,
        tuple(p.proposal_id for p in valid),
        tuple(r.rebuttal_id for r in rebuttals),
        tuple(sorted({p.domain for p in valid})),
        "Synthesized architecture from independently evidenced domain proposals.",
        changes,
        properties,
        evidence,
        concerns,
    )


def synthesis_ready(proposal: SynthesizedProposal) -> bool:
    return bool(
        proposal.source_proposal_ids
        and proposal.changes
        and proposal.target_properties
        and proposal.evidence
        and not proposal.unresolved_concerns
    )
