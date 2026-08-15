"""
Recommendation scoring.

This module provides deterministic scoring for recommendations based on
evidence signals, target impact, urgency, and risk.
"""

from __future__ import annotations

import math
import re
from datetime import datetime, timezone

from ..models import utcnow
from .models import EvidenceSignal, RecommendationRecord


SIGNAL_TYPE_WEIGHTS: dict[str, float] = {
    "SECURITY_FINDING": 1.00,
    "INCIDENT": 0.95,
    "TEST_FAILURE": 0.85,
    "PERFORMANCE_OBSERVATION": 0.75,
    "TELEMETRY_SIGNAL": 0.70,
    "CUSTOMER_FEEDBACK": 0.70,
    "COST_OBSERVATION": 0.60,
    "USAGE_METRIC": 0.55,
    "DOCUMENT": 0.30,
}

DEFAULT_SIGNAL_WEIGHT = 0.50

SEVERITY_WEIGHTS: dict[str, float] = {
    "LOW": 0.25,
    "MEDIUM": 0.50,
    "HIGH": 0.80,
    "CRITICAL": 1.00,
}

RECOMMENDATION_TYPE_IMPACT: dict[str, float] = {
    "SECURITY": 0.95,
    "RELIABILITY": 0.85,
    "ARCHITECTURE": 0.85,
    "INFRASTRUCTURE": 0.80,
    "PERFORMANCE": 0.75,
    "COST": 0.65,
    "DOCUMENTATION": 0.35,
    "GENERAL": 0.60,
}

RECOMMENDATION_TYPE_RISK_BASE: dict[str, float] = {
    "SECURITY": 0.80,
    "INFRASTRUCTURE": 0.70,
    "ARCHITECTURE": 0.65,
    "RELIABILITY": 0.65,
    "PERFORMANCE": 0.55,
    "COST": 0.45,
    "DOCUMENTATION": 0.20,
    "GENERAL": 0.50,
}


def normalize_tokens(text: str) -> set[str]:
    """Normalize text into lowercase tokens."""
    return {
        token
        for token in re.findall(r"[a-z0-9_]+", text.lower())
        if token
    }


def parse_timestamp(value: str | None) -> datetime | None:
    """Parse an ISO-8601 timestamp safely."""
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed


def recency_decay(signal: EvidenceSignal) -> float:
    """
    Compute recency decay.

    Recent evidence is weighted more strongly than old evidence.
    """

    observed_at = parse_timestamp(signal.observed_at)

    if not observed_at:
        return 0.80

    age_days = max(
        0.0,
        (utcnow() - observed_at).total_seconds() / 86_400.0,
    )

    return max(0.20, math.exp(-age_days / 90.0))


def signal_contribution(signal: EvidenceSignal) -> float:
    """Compute the contribution of one evidence signal."""

    signal_type_weight = SIGNAL_TYPE_WEIGHTS.get(
        signal.signal_type.upper(),
        DEFAULT_SIGNAL_WEIGHT,
    )

    severity_weight = SEVERITY_WEIGHTS.get(
        signal.severity.upper(),
        0.50,
    )

    return (
        signal_type_weight
        * severity_weight
        * signal.confidence
        * recency_decay(signal)
    )


def matches_recommendation(
    recommendation: RecommendationRecord,
    signal: EvidenceSignal,
) -> bool:
    """Return true if an evidence signal matches a recommendation."""

    if recommendation.id in signal.related_recommendation_ids:
        return True

    if signal.source_id in recommendation.evidence_refs:
        return True

    if signal.source_id in recommendation.source_entity_ids:
        return True

    return False


def evaluate_evidence(
    recommendation: RecommendationRecord,
    signals: list[EvidenceSignal],
) -> tuple[list[EvidenceSignal], float]:
    """
    Evaluate evidence for a recommendation.

    Returns matched signals and evidence score.
    """

    matched: list[EvidenceSignal] = []
    total = 0.0

    for signal in signals:
        if not matches_recommendation(recommendation, signal):
            continue

        matched.append(signal)
        total += signal_contribution(signal)

    source_diversity = len({signal.signal_type for signal in matched})

    score = min(
        1.0,
        (total / 1.5) + (source_diversity * 0.05),
    )

    return matched, score


def impact_score(recommendation: RecommendationRecord) -> float:
    """Estimate architectural or operational impact."""

    base = RECOMMENDATION_TYPE_IMPACT.get(
        recommendation.recommendation_type.upper(),
        0.60,
    )

    if recommendation.target_entity_id:
        base = min(1.0, base + 0.10)

    source_boost = min(0.15, len(recommendation.source_entity_ids) * 0.03)
    evidence_boost = min(0.10, len(recommendation.evidence_refs) * 0.02)

    return min(1.0, base + source_boost + evidence_boost)


def urgency_score(matched_signals: list[EvidenceSignal]) -> float:
    """Estimate urgency from matched evidence signals."""

    if not matched_signals:
        return 0.20

    max_severity = max(
        SEVERITY_WEIGHTS.get(signal.severity.upper(), 0.50)
        for signal in matched_signals
    )

    max_recency = max(
        recency_decay(signal)
        for signal in matched_signals
    )

    return min(1.0, (0.70 * max_severity) + (0.30 * max_recency))


def risk_score(
    recommendation: RecommendationRecord,
    matched_signals: list[EvidenceSignal],
    conflict_count: int,
    duplicate_count: int,
) -> float:
    """Estimate risk associated with a recommendation."""

    base = RECOMMENDATION_TYPE_RISK_BASE.get(
        recommendation.recommendation_type.upper(),
        0.50,
    )

    if matched_signals:
        average_severity = sum(
            SEVERITY_WEIGHTS.get(signal.severity.upper(), 0.50)
            for signal in matched_signals
        ) / len(matched_signals)
    else:
        average_severity = 0.0

    severity_factor = average_severity * 0.35
    conflict_factor = min(0.20, conflict_count * 0.10)
    duplicate_factor = min(0.10, duplicate_count * 0.03)

    return min(1.0, base + severity_factor + conflict_factor + duplicate_factor)


def priority_level(priority_score: float) -> str:
    """Map priority score to priority level."""

    if priority_score >= 0.70:
        return "HIGH"

    if priority_score >= 0.45:
        return "MEDIUM"

    return "LOW"


def risk_level(risk_score: float) -> str:
    """Map risk score to risk level."""

    if risk_score >= 0.85:
        return "CRITICAL"

    if risk_score >= 0.70:
        return "HIGH"

    if risk_score >= 0.45:
        return "MEDIUM"

    return "LOW"


def build_rationale(
    evidence_score: float,
    impact_score_value: float,
    urgency_score_value: float,
    matched_signals: list[EvidenceSignal],
) -> str:
    """Build a human-readable rationale."""

    return (
        f"Evidence strength {evidence_score:.2f}, "
        f"impact {impact_score_value:.2f}, "
        f"urgency {urgency_score_value:.2f}, "
        f"matched signals {len(matched_signals)}."
    )
