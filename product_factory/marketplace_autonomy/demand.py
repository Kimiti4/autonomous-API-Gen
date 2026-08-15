"""
Marketplace demand analysis.
"""

from __future__ import annotations

from typing import List

from .models import (
    DemandOpportunity,
    MarketplaceMetricSnapshot,
)


class DemandAnalyzer:
    """Identifies demand gaps and marketplace opportunities."""

    def analyze(
        self,
        snapshot: MarketplaceMetricSnapshot,
    ) -> List[DemandOpportunity]:
        opportunities: List[DemandOpportunity] = []

        for category, demand_score in snapshot.category_demand.items():
            product_count = snapshot.category_product_counts.get(category, 0)

            gap_score = demand_score / float(product_count + 1)

            recommendation = (
                f"Category '{category}' has demand score {demand_score:.2f} "
                f"and only {product_count} product(s). "
                "Consider generating or recruiting certified products for this category."
            )

            opportunities.append(
                DemandOpportunity(
                    marketplace_id=snapshot.marketplace_id,
                    category=category,
                    demand_score=demand_score,
                    product_count=product_count,
                    gap_score=round(gap_score, 4),
                    evidence_refs=[
                        f"marketplace:{snapshot.marketplace_id}",
                        f"category:{category}",
                    ],
                    recommendation=recommendation,
                )
            )

        opportunities.sort(key=lambda item: item.gap_score, reverse=True)

        return opportunities
