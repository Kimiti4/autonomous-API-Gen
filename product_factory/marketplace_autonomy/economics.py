"""
Marketplace economics engine.
"""

from __future__ import annotations

from typing import Dict, Optional

from .models import (
    MarketplaceAutonomyPolicy,
    MarketplaceMetricSnapshot,
    PricingModel,
    PricingPolicyChange,
)


class EconomicsEngine:
    """Validates and simulates marketplace economic changes."""

    def __init__(self, policy: MarketplaceAutonomyPolicy) -> None:
        self.policy = policy

    def validate_fee_change(
        self,
        current_fee_pct: float,
        proposed_fee_pct: float,
    ) -> PricingPolicyChange:
        if current_fee_pct < 0 or proposed_fee_pct < 0:
            raise ValueError("Fee percentages must be non-negative.")

        change_pct = abs(proposed_fee_pct - current_fee_pct)

        approval_required = False

        rationale = "Fee change within policy limits."

        if change_pct > self.policy.max_fee_change_pct:
            rationale = (
                f"Fee change {change_pct:.2f}% exceeds policy limit "
                f"{self.policy.max_fee_change_pct:.2f}%."
            )

            approval_required = True

        if self.policy.require_human_approval_for_fee_change:
            approval_required = True

        return PricingPolicyChange(
            current_fee_pct=current_fee_pct,
            proposed_fee_pct=proposed_fee_pct,
            rationale=rationale,
            expected_impact={},
            approval_required=approval_required,
        )

    def simulate_fee_change(
        self,
        snapshot: MarketplaceMetricSnapshot,
        current_fee_pct: float,
        proposed_fee_pct: float,
        elasticity: float = 0.30,
    ) -> Dict[str, float]:
        if current_fee_pct < 0 or proposed_fee_pct < 0:
            raise ValueError("Fee percentages must be non-negative.")

        change_ratio = (proposed_fee_pct - current_fee_pct) / 100.0

        demand_multiplier = max(0.0, 1.0 - (elasticity * change_ratio))

        current_net_revenue = snapshot.net_revenue

        projected_net_revenue = current_net_revenue * demand_multiplier

        return {
            "current_fee_pct": current_fee_pct,
            "proposed_fee_pct": proposed_fee_pct,
            "demand_multiplier": round(demand_multiplier, 4),
            "current_net_revenue": round(current_net_revenue, 2),
            "projected_net_revenue": round(projected_net_revenue, 2),
        }

    def propose_pricing_model(
        self,
        snapshot: MarketplaceMetricSnapshot,
        target_model: PricingModel,
    ) -> PricingPolicyChange:
        if target_model not in self.policy.allowed_pricing_models:
            raise ValueError(
                f"Pricing model {target_model.value} is not allowed by policy."
            )

        rationale = (
            f"Propose pricing model {target_model.value} based on marketplace metrics."
        )

        return PricingPolicyChange(
            pricing_model=target_model,
            rationale=rationale,
            expected_impact={
                "mrr_estimate": snapshot.mrr_estimate,
            },
            approval_required=True,
        )
