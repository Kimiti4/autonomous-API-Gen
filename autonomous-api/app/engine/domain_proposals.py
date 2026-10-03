"""Evidence-backed domain proposals and rebuttals."""
from __future__ import annotations
from dataclasses import dataclass
from .architectural_memory import ArchitectureMemory, MemoryIndex, index_memory


@dataclass(frozen=True)
class DomainProposal:
    proposal_id: str
    domain: str
    problem_signature: str
    claim: str
    changes: tuple[str, ...]
    target_properties: tuple[str, ...]
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class DomainRebuttal:
    rebuttal_id: str
    proposal_id: str
    domain: str
    concerns: tuple[str, ...]
    counterexample_ids: tuple[str, ...]
    evidence: tuple[str, ...]
    alternative_changes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProposalAssessment:
    proposal_id: str
    accepted_for_evaluation: bool
    reasons: tuple[str, ...]


def validate_proposal(proposal: DomainProposal) -> ProposalAssessment:
    reasons: list[str] = []
    if not proposal.evidence:
        reasons.append("proposal-requires-evidence")
    if not proposal.changes:
        reasons.append("proposal-requires-changes")
    if not proposal.target_properties:
        reasons.append("proposal-requires-target-properties")
    return ProposalAssessment(proposal.proposal_id, not reasons, tuple(reasons))


def validate_rebuttal(rebuttal: DomainRebuttal) -> tuple[str, ...]:
    errors: list[str] = []
    if not rebuttal.evidence:
        errors.append("rebuttal-requires-evidence")
    if not rebuttal.concerns and not rebuttal.counterexample_ids:
        errors.append("rebuttal-requires-concern-or-counterexample")
    return tuple(errors)


def record_domain_proposal(
    index: ArchitectureMemory,
    proposal: DomainProposal,
) -> ArchitectureMemory:
    assessment = validate_proposal(proposal)
    if not assessment.accepted_for_evaluation:
        raise ValueError(";".join(assessment.reasons))
    return index_memory(
        index,
        ArchitectureMemory(
            proposal.proposal_id,
            proposal.problem_signature,
            proposal.claim,
            (proposal.domain,),
            proposal.changes,
            "bounded",
            proposal.target_properties,
            proposal.evidence,
        ),
    )
