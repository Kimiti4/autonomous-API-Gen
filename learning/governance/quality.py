"""
Evidence quality gate.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from ..models import LearningInsight
from ..utils import utcnow
from .models import EvidenceQualityReport, LearningGovernancePolicy


def parse_timestamp(value: str) -> datetime | None:
    """Parse ISO timestamp safely."""

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed


class EvidenceQualityGate:
    """Evaluates the quality of learning evidence."""

    def __init__(self, policy: LearningGovernancePolicy) -> None:
        self.policy = policy

    def evaluate(
        self,
        bundle_id: str,
        insights: List[LearningInsight],
    ) -> EvidenceQualityReport:
        if not insights:
            return EvidenceQualityReport(
                bundle_id=bundle_id,
                evidence_count=0,
                poisoning_indicators=["no_evidence"],
                passed=False,
            )

        confidences = [insight.confidence for insight in insights]

        average_confidence = sum(confidences) / len(confidences)

        corroboration_scores = [
            min(1.0, len(insight.signal_ids) / 2.0)
            for insight in insights
        ]

        corroboration_score = (
            sum(corroboration_scores) / len(corroboration_scores)
            if corroboration_scores
            else 0.0
        )

        now = utcnow()

        recency_scores: List[float] = []

        for insight in insights:
            created_at = parse_timestamp(insight.created_at)

            if not created_at:
                recency_scores.append(0.5)
                continue

            age_hours = max(
                0.0,
                (now - created_at).total_seconds() / 3600.0,
            )

            if age_hours <= self.policy.max_evidence_age_hours:
                recency_scores.append(1.0)
            else:
                overflow = age_hours - self.policy.max_evidence_age_hours

                recency_scores.append(
                    max(
                        0.0,
                        1.0 - (overflow / self.policy.max_evidence_age_hours),
                    )
                )

        recency_score = (
            sum(recency_scores) / len(recency_scores)
            if recency_scores
            else 0.0
        )

        quality_score = (
            (0.60 * average_confidence)
            + (0.20 * corroboration_score)
            + (0.20 * recency_score)
        )

        poisoning_indicators: List[str] = []

        if len(insights) > self.policy.max_insights_per_sync:
            poisoning_indicators.append("excessive_insight_volume")

        if average_confidence < self.policy.min_confidence:
            poisoning_indicators.append("low_confidence_evidence")

        if corroboration_score < self.policy.min_corroboration:
            poisoning_indicators.append("weak_corroboration")

        # NOTE: a single low-confidence insight must not silently clear the
        # quality gate. The `min_confidence` floor applies per-insight so that
        # a low-quality signal poisons the batch and blocks governed sync
        # (see test_low_quality_evidence_blocks_sync).
        passed = (
            quality_score >= self.policy.min_quality_score
            and average_confidence >= self.policy.min_confidence
            and min(confidences) >= self.policy.min_confidence
            and len(insights) <= self.policy.max_insights_per_sync
        )

        return EvidenceQualityReport(
            bundle_id=bundle_id,
            evidence_count=len(insights),
            average_confidence=round(average_confidence, 4),
            corroboration_score=round(corroboration_score, 4),
            recency_score=round(recency_score, 4),
            quality_score=round(quality_score, 4),
            poisoning_indicators=poisoning_indicators,
            passed=passed,
        )
