"""
Marketplace fraud detection.
"""

from __future__ import annotations

from typing import List

from .models import (
    FraudAssessment,
    ListingRankingContext,
    MarketplaceAutonomyPolicy,
)


class FraudDetectionEngine:
    """Detects potential marketplace fraud and trust risk."""

    def __init__(self, policy: MarketplaceAutonomyPolicy) -> None:
        self.policy = policy

    def assess_listing(
        self,
        listing: ListingRankingContext,
    ) -> FraudAssessment:
        indicators: List[str] = []

        fraud_score = 0.0

        if not listing.certified:
            fraud_score += 0.25
            indicators.append("listing_not_certified")

        if listing.security_score < 0.5:
            fraud_score += 0.20
            indicators.append("low_security_score")

        if listing.refund_rate > self.policy.refund_rate_alert_threshold:
            fraud_score += 0.30
            indicators.append("high_refund_rate")

        if listing.fraud_score > 0.0:
            fraud_score += listing.fraud_score * 0.5
            indicators.append("prior_fraud_signals")

        if listing.support_health < 0.3:
            fraud_score += 0.10
            indicators.append("poor_support_health")

        fraud_score = min(1.0, fraud_score)

        severity = "LOW"

        if fraud_score >= self.policy.fraud_score_alert_threshold:
            severity = "HIGH"
        elif fraud_score >= 0.40:
            severity = "MEDIUM"

        recommended_action = "MONITOR"

        if fraud_score >= self.policy.fraud_score_alert_threshold:
            recommended_action = "RESTRICT_AND_REVIEW"
        elif fraud_score >= 0.40:
            recommended_action = "REVIEW"

        return FraudAssessment(
            entity_id=listing.listing_id,
            fraud_score=round(fraud_score, 4),
            indicators=indicators,
            severity=severity,
            recommended_action=recommended_action,
        )
