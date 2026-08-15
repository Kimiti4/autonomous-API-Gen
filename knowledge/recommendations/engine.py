"""
Recommendation analytics engine.

This engine performs read-only analytics over recommendations and evidence
signals.

It does not execute recommendations.
"""

from __future__ import annotations

from typing import Optional

from ..auth import Actor
from ..ids import deterministic_id
from ..models import utcnow
from .conflicts import find_conflicts
from .dedupe import find_duplicate_clusters
from .models import (
    RankedRecommendation,
    RecommendationAnalyticsMetadata,
    RecommendationAnalyticsRequest,
    RecommendationAnalyticsResult,
    RecommendationPacket,
)
from .scoring import (
    build_rationale,
    evaluate_evidence,
    impact_score,
    priority_level,
    risk_level,
    risk_score,
    urgency_score,
)


SENSITIVE_LEVELS = {"CONFIDENTIAL", "RESTRICTED"}
SENSITIVE_VIEWER_ROLES = {"knowledge_auditor", "knowledge_admin"}


class RecommendationAnalyticsEngine:
    """Read-only recommendation analytics engine."""

    def analyze(
        self,
        request: RecommendationAnalyticsRequest,
        actor: Optional[Actor] = None,
    ) -> RecommendationAnalyticsResult:
        """Analyze recommendations."""

        request_id = deterministic_id(
            "recommendation_analytics",
            request.model_dump(mode="json"),
        )

        authorized_recommendations = []
        excluded_sensitive_count = 0

        for recommendation in request.recommendations:
            if (
                request.redact_sensitive
                and recommendation.sensitivity.upper() in SENSITIVE_LEVELS
                and not self._can_view_sensitive(actor)
            ):
                excluded_sensitive_count += 1
                continue

            authorized_recommendations.append(recommendation)

        duplicate_clusters = find_duplicate_clusters(
            authorized_recommendations,
            request.duplicate_threshold,
        )

        conflicts = find_conflicts(authorized_recommendations)

        duplicate_counts: dict[str, int] = {}
        for cluster in duplicate_clusters:
            for recommendation_id in cluster.recommendation_ids:
                duplicate_counts[recommendation_id] = (
                    duplicate_counts.get(recommendation_id, 0) + 1
                )

        conflict_counts: dict[str, int] = {}
        for conflict in conflicts:
            for recommendation_id in conflict.recommendation_ids:
                conflict_counts[recommendation_id] = (
                    conflict_counts.get(recommendation_id, 0) + 1
                )

        ranked_recommendations: list[RankedRecommendation] = []

        for recommendation in authorized_recommendations:
            matched_signals, evidence_score_value = evaluate_evidence(
                recommendation,
                request.signals,
            )

            impact_score_value = impact_score(recommendation)
            urgency_score_value = urgency_score(matched_signals)

            priority_score_value = round(
                min(
                    1.0,
                    (0.45 * evidence_score_value)
                    + (0.30 * impact_score_value)
                    + (0.25 * urgency_score_value),
                ),
                4,
            )

            risk_score_value = risk_score(
                recommendation,
                matched_signals,
                conflict_counts.get(recommendation.id, 0),
                duplicate_counts.get(recommendation.id, 0),
            )

            ranked_recommendations.append(
                RankedRecommendation(
                    recommendation=recommendation,
                    evidence_score=round(evidence_score_value, 4),
                    impact_score=round(impact_score_value, 4),
                    urgency_score=round(urgency_score_value, 4),
                    priority_score=priority_score_value,
                    risk_score=round(risk_score_value, 4),
                    priority_level=priority_level(priority_score_value),
                    risk_level=risk_level(risk_score_value),
                    matched_signals=matched_signals,
                    rationale=build_rationale(
                        evidence_score_value,
                        impact_score_value,
                        urgency_score_value,
                        matched_signals,
                    ),
                )
            )

        ranked_recommendations.sort(
            key=lambda item: (
                -item.priority_score,
                -item.risk_score,
                item.recommendation.title,
            )
        )

        ranked_recommendations = ranked_recommendations[: request.max_results]

        packet: Optional[RecommendationPacket] = None

        if request.include_packet:
            packet_id = deterministic_id(
                "recommendation_packet",
                {
                    "request_id": request_id,
                    "ranked_recommendation_ids": [
                        ranked.recommendation.id
                        for ranked in ranked_recommendations
                    ],
                },
            )

            packet = RecommendationPacket(
                packet_id=packet_id,
                created_at=utcnow().isoformat(),
                context=request.context,
                ranked_recommendations=ranked_recommendations,
                duplicate_clusters=duplicate_clusters,
                conflicts=conflicts,
                governance_status="DRAFT",
                submission_constraints=[
                    "Recommendations must be submitted through the Phase 28 Governance Kernel.",
                    "Recommendations must not directly mutate the ISR.",
                    "Duplicate clusters should be resolved before approval.",
                    "Conflicting recommendations require explicit resolution.",
                    "Evidence references must remain traceable.",
                ],
            )

        metadata = RecommendationAnalyticsMetadata(
            request_id=request_id,
            total_recommendations=len(request.recommendations),
            analyzed_recommendations=len(authorized_recommendations),
            excluded_sensitive_count=excluded_sensitive_count,
            duplicate_cluster_count=len(duplicate_clusters),
            conflict_count=len(conflicts),
            generated_at=utcnow().isoformat(),
        )

        return RecommendationAnalyticsResult(
            metadata=metadata,
            ranked_recommendations=ranked_recommendations,
            duplicate_clusters=duplicate_clusters,
            conflicts=conflicts,
            packet=packet,
        )

    def _can_view_sensitive(self, actor: Optional[Actor]) -> bool:
        if not actor:
            return False

        return any(actor.has_role(role) for role in SENSITIVE_VIEWER_ROLES)
