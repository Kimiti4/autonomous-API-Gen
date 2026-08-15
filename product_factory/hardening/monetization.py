"""
Phase 24.5 — Monetization, Billing, and Revenue Operations Hardening.
"""

from __future__ import annotations

from typing import Dict, List

from ..utils import utcnow
from .models import (
    BillingEvent,
    BillingPolicy,
    Entitlement,
    PricingPolicy,
    RevenueOpsReport,
)


class MonetizationOpsEngine:
    """Engine for monetization governance and revenue operations."""

    def __init__(
        self,
        pricing_policy: PricingPolicy | None = None,
        billing_policy: BillingPolicy | None = None,
    ) -> None:
        self.pricing_policy = pricing_policy or PricingPolicy()
        self.billing_policy = billing_policy or BillingPolicy()

        self.entitlements: Dict[str, Entitlement] = {}
        self.billing_events: List[BillingEvent] = []

    def validate_pricing_plan(self, plan: Dict) -> Dict:
        issues: List[str] = []

        model = plan.get("model")

        if model not in self.pricing_policy.allowed_models:
            issues.append(
                f"Pricing model {model} is not allowed by policy."
            )

        tiers = plan.get("tiers", [])

        if not tiers:
            issues.append("Pricing plan has no tiers.")

        for tier in tiers:
            tier_name = tier.get("name", "unnamed")

            price = tier.get("price", 0.0)

            currency = tier.get("currency", self.pricing_policy.currency)

            if price < 0:
                issues.append(f"Tier {tier_name} has negative price.")

            if currency != self.pricing_policy.currency:
                issues.append(
                    f"Tier {tier_name} uses unsupported currency {currency}."
                )

        return {
            "allowed": len(issues) == 0,
            "issues": issues,
        }

    def validate_price_change(
        self,
        old_plan: Dict,
        new_plan: Dict,
    ) -> Dict:
        old_tiers = {
            tier.get("id") or tier.get("name"): tier
            for tier in old_plan.get("tiers", [])
        }

        issues: List[str] = []
        warnings: List[str] = []
        approval_required = False

        for new_tier in new_plan.get("tiers", []):
            tier_key = new_tier.get("id") or new_tier.get("name")

            old_tier = old_tiers.get(tier_key)

            if not old_tier:
                warnings.append(f"New tier added: {tier_key}")
                continue

            old_price = float(old_tier.get("price", 0.0))
            new_price = float(new_tier.get("price", 0.0))

            if old_price <= 0:
                continue

            pct_change = abs(new_price - old_price) / old_price * 100.0

            if pct_change > self.pricing_policy.max_price_change_pct:
                message = (
                    f"Tier {tier_key} price change {pct_change:.2f}% exceeds "
                    f"policy limit "
                    f"{self.pricing_policy.max_price_change_pct:.2f}%."
                )

                issues.append(message)

                if self.pricing_policy.require_approval_for_price_change:
                    approval_required = True

        allowed = len(issues) == 0 or not approval_required

        return {
            "allowed": allowed,
            "approval_required": approval_required,
            "issues": issues,
            "warnings": warnings,
        }

    def ingest_billing_events(self, events: List[BillingEvent]) -> int:
        self.billing_events.extend(events)
        return len(events)

    def revenue_ops_report(self, product_id: str) -> RevenueOpsReport:
        product_events = [
            event
            for event in self.billing_events
            if event.product_id == product_id
        ]

        successful_payments = [
            event
            for event in product_events
            if event.event_type == "payment_succeeded"
        ]

        failed_payments = [
            event
            for event in product_events
            if event.event_type == "payment_failed"
        ]

        cancellations = [
            event
            for event in product_events
            if event.event_type == "subscription_cancelled"
        ]

        recognized_revenue = round(
            sum(event.amount for event in successful_payments),
            2,
        )

        alerts: List[str] = []
        recommendations: List[str] = []

        if failed_payments:
            alerts.append("Failed payments detected.")
            recommendations.append("Start dunning workflow.")

        if cancellations:
            alerts.append("Subscription cancellations detected.")
            recommendations.append("Trigger retention workflow.")

        if recognized_revenue == 0:
            recommendations.append("Validate monetization funnel.")

        return RevenueOpsReport(
            product_id=product_id,
            successful_payments=len(successful_payments),
            failed_payments=len(failed_payments),
            cancellations=len(cancellations),
            recognized_revenue=recognized_revenue,
            mrr_estimate=recognized_revenue,
            alerts=alerts,
            recommendations=recommendations,
            created_at=utcnow().isoformat(),
        )
