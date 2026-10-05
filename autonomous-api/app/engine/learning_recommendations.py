"""Evidence-bounded learning recommendations.

Historical patterns may rank options, but never authorize mutations or certify
current behavior. Recommendations retain provenance and explicitly distinguish
observation from current verification.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable

from .evidence_bounded_learning import LearningRecord


@dataclass(frozen=True)
class LearningRecommendation:
    record_id: str
    statement: str
    reason: str
    historical_evidence: tuple[str, ...]
    status: str = "advisory-only"


def derive_learning_recommendations(
    records: Iterable[LearningRecord],
    *,
    project_id: str,
    kind: str | None = None,
) -> tuple[LearningRecommendation, ...]:
    selected = [
        r for r in records
        if r.project_id == project_id and (kind is None or r.kind == kind)
    ]
    return tuple(
        LearningRecommendation(
            r.record_id,
            r.statement,
            f"Historical outcome: {r.outcome}",
            r.evidence_ids,
        )
        for r in sorted(selected, key=lambda x: x.record_id)
    )


def authorize_recommendation_as_current(
    recommendation: LearningRecommendation,
    current_evidence_ids: tuple[str, ...],
) -> None:
    if recommendation.status != "advisory-only":
        raise ValueError("invalid-learning-recommendation-status")
    if not current_evidence_ids:
        raise ValueError("learning-requires-current-evidence")
