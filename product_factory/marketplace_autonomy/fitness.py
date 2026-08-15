"""
Marketplace fitness evaluation.
"""

from __future__ import annotations

from typing import List

from .models import (
    MarketplaceAutonomyPolicy,
    MarketplaceFitnessReport,
    MarketplaceMetricSnapshot,
)


class MarketplaceFitnessEvaluator:
    """Evaluates marketplace health using multi-objective fitness."""

    def __init__(self, policy: MarketplaceAutonomyPolicy) -> None:
        self.policy = policy

    def evaluate(
        self,
        snapshot: MarketplaceMetricSnapshot,
    ) -> MarketplaceFitnessReport:
        alerts: List[str] = []
        recommendations: List[str] = []

        listing_count = max(snapshot.listing_count, 0)
        published_listing_count = max(snapshot.published_listing_count, 0)
        certified_listing_count = max(snapshot.certified_listing_count, 0)

        certification_coverage = (
            certified_listing_count / published_listing_count
            if published_listing_count > 0
            else 0.0
        )

        refund_rate = (
            snapshot.refund_count / snapshot.sales_count
            if snapshot.sales_count > 0
            else 0.0
        )

        conversion_quality = min(1.0, max(0.0, snapshot.conversion_rate))

        revenue_health = 0.0

        if snapshot.net_revenue > 0:
            revenue_health = 1.0
        elif snapshot.gross_revenue > 0:
            revenue_health = 0.5

        support_burden = 0.0

        if snapshot.sales_count > 0:
            support_burden = min(
                1.0,
                snapshot.support_ticket_count / snapshot.sales_count,
            )

        support_health = max(0.0, 1.0 - support_burden)

        trust = max(
            0.0,
            min(
                1.0,
                (
                    (1.0 - refund_rate)
                    + certification_coverage
                    + max(0.0, min(1.0, snapshot.average_rating / 5.0))
                )
                / 3.0,
            ),
        )

        liquidity = 0.0

        if published_listing_count > 0 and snapshot.sales_count > 0:
            liquidity = min(1.0, snapshot.sales_count / published_listing_count)

        diversity = 0.0

        category_counts = snapshot.category_product_counts.values()

        if category_counts:
            max_count = max(category_counts)
            total = sum(category_counts)

            if total > 0:
                diversity = 1.0 - (max_count / total)

        novelty = 0.5

        objectives = {
            "liquidity": round(liquidity, 4),
            "conversion_quality": round(conversion_quality, 4),
            "certification_coverage": round(certification_coverage, 4),
            "revenue_health": round(revenue_health, 4),
            "trust": round(trust, 4),
            "support_health": round(support_health, 4),
            "diversity": round(diversity, 4),
            "novelty": round(novelty, 4),
        }

        refund_ok = refund_rate <= self.policy.refund_rate_alert_threshold

        certification_ok = (
            certification_coverage
            >= self.policy.min_certification_score_for_featured_listing
        )

        fraud_ok = snapshot.fraud_alert_count == 0

        constraints = {
            "refund_rate_ok": refund_ok,
            "certification_coverage_ok": certification_ok,
            "fraud_under_control": fraud_ok,
            "published_listings_exist": published_listing_count > 0,
        }

        if not refund_ok:
            alerts.append("Refund rate exceeds threshold.")
            recommendations.append("Tighten curation and refund policies.")

        if not certification_ok:
            alerts.append("Certification coverage is below target.")
            recommendations.append("Require certification for featured listings.")

        if not fraud_ok:
            alerts.append("Fraud alerts are present.")
            recommendations.append("Increase fraud review controls.")

        if liquidity < 0.1:
            recommendations.append("Improve demand generation or listing quality.")

        if conversion_quality < 0.02:
            recommendations.append("Improve product pages, pricing, or ranking.")

        return MarketplaceFitnessReport(
            marketplace_id=snapshot.marketplace_id,
            objectives=objectives,
            constraints=constraints,
            alerts=alerts,
            recommendations=recommendations,
        )
