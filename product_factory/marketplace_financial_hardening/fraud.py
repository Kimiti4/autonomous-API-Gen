"""
Fraud vendor adapter framework and fraud control engine.

Fraud assessments are delegated to a pluggable adapter and then mapped to
marketplace actions (ALLOW / REVIEW / HOLD / BLOCK) under policy.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .models import (
    FraudAction,
    FraudAssessment,
    MarketplaceFinancialPolicy,
)


class FraudProviderAdapter:
    """Base contract for a fraud provider adapter."""

    def assess(
        self,
        listing_id: str,
        tenant_id: str,
        order_id: Optional[str] = None,
        context: Optional[Dict] = None,
    ) -> Dict:
        raise NotImplementedError


class NoopFraudAdapter(FraudProviderAdapter):
    """Default no-op fraud adapter (score 0, ALLOW)."""

    def assess(
        self,
        listing_id: str,
        tenant_id: str,
        order_id: Optional[str] = None,
        context: Optional[Dict] = None,
    ) -> Dict:
        return {
            "provider": "noop",
            "fraud_score": 0.0,
            "risk_indicators": [],
            "provider_reference": None,
        }


class FraudControlEngine:
    """Requests fraud assessments and enforces fraud policy actions."""

    def __init__(
        self,
        fraud_adapter: Optional[FraudProviderAdapter] = None,
        policy: Optional[MarketplaceFinancialPolicy] = None,
        governance=None,
    ) -> None:
        self.fraud_adapter = fraud_adapter or NoopFraudAdapter()
        self.policy = policy or MarketplaceFinancialPolicy()
        self.governance = governance

        self._assessments: Dict[str, FraudAssessment] = {}
        self.held_listings: List[str] = []
        self.blocked_listings: List[str] = []

    def assess(
        self,
        listing_id: str,
        tenant_id: str,
        order_id: Optional[str] = None,
        context: Optional[Dict] = None,
    ) -> FraudAssessment:
        raw = self.fraud_adapter.assess(
            listing_id=listing_id,
            tenant_id=tenant_id,
            order_id=order_id,
            context=context or {},
        )

        fraud_score = float(raw.get("fraud_score", 0.0))

        action = self._map_action(fraud_score)

        assessment = FraudAssessment(
            listing_id=listing_id,
            tenant_id=tenant_id,
            order_id=order_id,
            provider=raw.get("provider", "unknown"),
            fraud_score=round(max(0.0, min(1.0, fraud_score)), 4),
            risk_indicators=list(raw.get("risk_indicators", [])),
            action=action,
            provider_reference=raw.get("provider_reference"),
        )

        self._assessments[assessment.assessment_id] = assessment

        if action == FraudAction.HOLD:
            if listing_id not in self.held_listings:
                self.held_listings.append(listing_id)
        elif action == FraudAction.BLOCK:
            if listing_id not in self.blocked_listings:
                self.blocked_listings.append(listing_id)
            if listing_id in self.held_listings:
                self.held_listings.remove(listing_id)

        return assessment

    def is_blocked(self, listing_id: str) -> bool:
        return listing_id in self.blocked_listings

    def is_held(self, listing_id: str) -> bool:
        return listing_id in self.held_listings

    def assessments(self) -> List[FraudAssessment]:
        return list(self._assessments.values())

    def _map_action(self, fraud_score: float) -> FraudAction:
        if fraud_score >= self.policy.min_fraud_score_to_block:
            return FraudAction.BLOCK
        if fraud_score >= self.policy.min_fraud_score_to_hold:
            return FraudAction.HOLD
        if fraud_score >= 0.40:
            return FraudAction.REVIEW
        return FraudAction.ALLOW
