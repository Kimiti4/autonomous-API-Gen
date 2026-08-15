"""
Cross-marketplace routing engine.
"""

from __future__ import annotations

from typing import List

from .federation import FederationEngine
from .models import RoutingDecision, RoutingRequest
from .partners import PartnerEngine


class RoutingEngine:
    """Evaluates cross-marketplace routing decisions."""

    def __init__(
        self,
        federation_engine: FederationEngine,
        partner_engine: PartnerEngine | None = None,
    ) -> None:
        self.federation_engine = federation_engine
        self.partner_engine = partner_engine

    def evaluate(self, request: RoutingRequest) -> RoutingDecision:
        treaties = self.federation_engine.active_treaties_for(
            request.source_marketplace_id
        )

        candidates = request.candidate_marketplace_ids

        if not candidates:
            candidates = [
                treaty.target_marketplace_id
                for treaty in treaties
            ]

        if not candidates:
            raise ValueError("No candidate marketplaces available.")

        best_marketplace = None
        best_score = -1.0
        best_reasons: List[str] = []

        for candidate in candidates:
            treaty = next(
                (
                    t
                    for t in treaties
                    if t.target_marketplace_id == candidate
                ),
                None,
            )

            if not treaty:
                score = 0.0
                reasons = ["No active federation treaty."]
            else:
                score = 0.5
                reasons = ["Active federation treaty."]

                revenue_bonus = min(treaty.revenue_share_pct, 100.0) / 100.0
                score += revenue_bonus * 0.3
                reasons.append(
                    f"Revenue share: {treaty.revenue_share_pct:.2f}%"
                )

                if request.partner_id and self.partner_engine:
                    try:
                        partner = self.partner_engine.get_partner(
                            request.partner_id
                        )

                        if partner.status.value == "ACTIVE":
                            score += partner.trust_score * 0.2
                            reasons.append(
                                f"Partner trust score: {partner.trust_score:.2f}"
                            )
                    except KeyError:
                        reasons.append("Partner not found.")

            if score > best_score:
                best_score = score
                best_marketplace = candidate
                best_reasons = reasons

        if not best_marketplace or best_score <= 0.0:
            raise ValueError("No routable marketplace found.")

        return RoutingDecision(
            source_marketplace_id=request.source_marketplace_id,
            product_id=request.product_id,
            selected_marketplace_id=best_marketplace,
            score=round(best_score, 4),
            reasons=best_reasons,
        )
