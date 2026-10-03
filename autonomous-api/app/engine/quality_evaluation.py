"""Requirement-driven engineering quality evaluation."""
from __future__ import annotations
from dataclasses import dataclass


QUALITY_DIMENSIONS = (
    "correctness", "security", "performance", "reliability",
    "maintainability", "operability", "accessibility", "complexity", "cost",
)


@dataclass(frozen=True)
class QualityCriterion:
    dimension: str
    requirement_ids: tuple[str, ...]
    claims: tuple[str, ...]
    required_evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class QualityAssessment:
    alternative_id: str
    dimension: str
    status: str
    evidence_ids: tuple[str, ...]
    unresolved: tuple[str, ...]
    observations: tuple[str, ...]


def build_quality_criteria(
    requirements: dict[str, tuple[str, ...]],
) -> tuple[QualityCriterion, ...]:
    criteria = []
    for dimension in QUALITY_DIMENSIONS:
        ids = tuple(requirements.get(dimension, ()))
        if ids:
            criteria.append(QualityCriterion(
                dimension, ids,
                tuple(f"demonstrate {dimension} requirement {rid}" for rid in ids),
            ))
    return tuple(criteria)


def assess_quality(
    alternative_id: str,
    criterion: QualityCriterion,
    satisfied_requirement_ids: tuple[str, ...],
    evidence_ids: tuple[str, ...],
    observations: tuple[str, ...] = (),
) -> QualityAssessment:
    satisfied = set(satisfied_requirement_ids)
    unresolved = tuple(r for r in criterion.requirement_ids if r not in satisfied)
    status = "SUPPORTED" if not unresolved and evidence_ids else "INCONCLUSIVE"
    return QualityAssessment(
        alternative_id, criterion.dimension, status, evidence_ids,
        unresolved, observations,
    )


def aggregate_quality(
    assessments: tuple[QualityAssessment, ...],
) -> str:
    if not assessments:
        return "INCONCLUSIVE"
    if any(a.status == "INCONCLUSIVE" for a in assessments):
        return "INCONCLUSIVE"
    return "SUPPORTED"
