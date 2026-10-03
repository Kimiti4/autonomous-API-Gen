"""Multi-dimensional engineering candidate comparison without a single score."""
from __future__ import annotations
from dataclasses import dataclass


DIMENSIONS = (
    "correctness", "security", "reliability", "performance",
    "maintainability", "complexity", "architecture_compatibility",
)


@dataclass(frozen=True)
class DimensionEvidence:
    dimension: str
    status: str  # supported, contradicted, unverified, bounded
    evidence_ids: tuple[str, ...] = ()
    notes: str = ""


@dataclass(frozen=True)
class CandidateAssessment:
    candidate_id: str
    evidence: tuple[DimensionEvidence, ...]
    unresolved_risks: tuple[str, ...] = ()


@dataclass(frozen=True)
class CandidateComparison:
    candidate_ids: tuple[str, ...]
    dimensions: tuple[str, ...]
    assessments: tuple[CandidateAssessment, ...]


def validate_assessment(assessment: CandidateAssessment) -> tuple[str, ...]:
    errors = []
    seen = set()
    for item in assessment.evidence:
        if item.dimension not in DIMENSIONS:
            errors.append(f"unknown-dimension:{item.dimension}")
        if item.dimension in seen:
            errors.append(f"duplicate-dimension:{item.dimension}")
        seen.add(item.dimension)
        if item.status not in {"supported", "contradicted", "unverified", "bounded"}:
            errors.append(f"invalid-status:{item.dimension}")
    return tuple(errors)


def compare_candidates(
    assessments: tuple[CandidateAssessment, ...],
) -> CandidateComparison:
    return CandidateComparison(
        tuple(a.candidate_id for a in assessments),
        DIMENSIONS,
        assessments,
    )


def unresolved_dimensions(assessment: CandidateAssessment) -> tuple[str, ...]:
    return tuple(
        e.dimension for e in assessment.evidence
        if e.status in {"unverified", "bounded"}
    )


def can_be_governed_for_evolution(assessment: CandidateAssessment) -> bool:
    if validate_assessment(assessment):
        return False
    return not any(
        e.status == "contradicted" for e in assessment.evidence
    )
