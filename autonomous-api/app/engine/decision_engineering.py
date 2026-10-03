"""Evidence-backed engineering alternative evaluation and selection."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class EngineeringAlternative:
    alternative_id: str
    description: str
    satisfies: tuple[str, ...] = ()
    tradeoffs: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    required_evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class AlternativeAssessment:
    alternative_id: str
    evidence_ids: tuple[str, ...]
    satisfied_requirements: tuple[str, ...]
    unresolved_requirements: tuple[str, ...]
    risks: tuple[str, ...]
    status: str


@dataclass(frozen=True)
class EngineeringDecision:
    decision_id: str
    selected_alternative_id: str
    assessments: tuple[AlternativeAssessment, ...]
    rationale: tuple[str, ...]
    authorization_required: bool = True


def assess_alternative(
    alternative: EngineeringAlternative,
    evidence_ids: tuple[str, ...],
    verified_requirements: tuple[str, ...],
) -> AlternativeAssessment:
    verified = set(verified_requirements)
    satisfied = tuple(x for x in alternative.satisfies if x in verified)
    unresolved = tuple(x for x in alternative.satisfies if x not in verified)
    status = "SUPPORTED" if not unresolved else "INCONCLUSIVE"
    return AlternativeAssessment(
        alternative.alternative_id,
        evidence_ids,
        satisfied,
        unresolved,
        alternative.risks,
        status,
    )


def propose_decision(
    decision_id: str,
    alternatives: tuple[AlternativeAssessment, ...],
    selected_alternative_id: str,
    rationale: tuple[str, ...],
) -> EngineeringDecision:
    if not alternatives:
        raise ValueError("at least one alternative is required")
    ids = {a.alternative_id for a in alternatives}
    if selected_alternative_id not in ids:
        raise ValueError("selected alternative is not present")
    selected = next(a for a in alternatives if a.alternative_id == selected_alternative_id)
    if selected.status != "SUPPORTED":
        raise ValueError("cannot select an unsupported or inconclusive alternative")
    if not rationale:
        raise ValueError("selection rationale is required")
    return EngineeringDecision(
        decision_id,
        selected_alternative_id,
        alternatives,
        rationale,
        authorization_required=True,
    )
