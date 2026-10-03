"""Evidence-backed discovery and promotion of engineering invariants."""
from __future__ import annotations
from dataclasses import dataclass
from .invariant_contracts import Invariant, InvariantContract, validate_contract


@dataclass(frozen=True)
class InvariantCandidate:
    candidate_id: str
    domain: str
    description: str
    trigger_ids: tuple[str, ...]
    supporting_evidence: tuple[str, ...]
    proposed_property: str


@dataclass(frozen=True)
class InvariantPromotion:
    candidate_id: str
    invariant: Invariant
    validation_ids: tuple[str, ...]


def discover_candidate(
    candidate_id: str,
    domain: str,
    description: str,
    trigger_ids: tuple[str, ...],
    supporting_evidence: tuple[str, ...],
    proposed_property: str,
) -> InvariantCandidate:
    if not trigger_ids:
        raise ValueError("invariant-candidate-requires-trigger")
    if not supporting_evidence:
        raise ValueError("invariant-candidate-requires-evidence")
    if not proposed_property:
        raise ValueError("invariant-candidate-requires-property")
    return InvariantCandidate(
        candidate_id, domain, description, trigger_ids,
        supporting_evidence, proposed_property,
    )


def promote_candidate(
    candidate: InvariantCandidate,
    validation_ids: tuple[str, ...],
) -> InvariantPromotion:
    if not validation_ids:
        raise ValueError("invariant-promotion-requires-validation")
    invariant = Invariant(
        invariant_id=candidate.candidate_id,
        domain=candidate.domain,
        description=candidate.description,
        evidence=tuple(sorted(set(
            candidate.supporting_evidence + validation_ids
        ))),
    )
    validate_contract(InvariantContract(candidate.domain, (invariant,)))
    return InvariantPromotion(candidate.candidate_id, invariant, validation_ids)
