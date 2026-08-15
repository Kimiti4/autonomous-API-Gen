"""
Marketplace ranking engine.
"""

from __future__ import annotations

from typing import Dict, List

from .models import (
    ListingRankingContext,
    MarketplaceAutonomyPolicy,
    RankedListing,
    RankingPolicy,
)


class RankingEngine:
    """Ranks marketplace listings under quality and trust constraints."""

    def __init__(
        self,
        autonomy_policy: MarketplaceAutonomyPolicy,
        ranking_policy: RankingPolicy | None = None,
    ) -> None:
        self.autonomy_policy = autonomy_policy
        self.ranking_policy = ranking_policy or RankingPolicy()

    def rank_listings(
        self,
        listings: List[ListingRankingContext],
    ) -> List[RankedListing]:
        ranked: List[RankedListing] = []

        for listing in listings:
            exclusion_reasons: List[str] = []

            if (
                self.ranking_policy.require_certified
                and not listing.certified
            ):
                exclusion_reasons.append("Listing is not certified.")

            if (
                self.ranking_policy.block_fraud_flagged
                and listing.fraud_score
                >= self.autonomy_policy.fraud_score_alert_threshold
            ):
                exclusion_reasons.append("Listing has a high fraud score.")

            if (
                listing.certification_score
                < self.autonomy_policy.min_certification_score_for_featured_listing
            ):
                exclusion_reasons.append(
                    "Certification score below featured listing threshold."
                )

            feature_contributions: Dict[str, float] = {}

            score = 0.0

            for feature, weight in self.ranking_policy.weights.items():
                value = float(getattr(listing, feature, 0.0))

                contribution = value * weight

                feature_contributions[feature] = round(contribution, 4)

                score += contribution

            explanation_parts = []

            if self.ranking_policy.explanation_required:
                sorted_features = sorted(
                    feature_contributions.items(),
                    key=lambda item: item[1],
                    reverse=True,
                )

                for feature, contribution in sorted_features[:3]:
                    explanation_parts.append(
                        f"{feature}:{contribution:.3f}"
                    )

            explanation = "; ".join(explanation_parts)

            ranked.append(
                RankedListing(
                    listing_id=listing.listing_id,
                    score=round(score, 4),
                    included=len(exclusion_reasons) == 0,
                    exclusion_reasons=exclusion_reasons,
                    feature_contributions=feature_contributions,
                    explanation=explanation,
                )
            )

        ranked.sort(key=lambda item: item.score, reverse=True)

        return ranked
