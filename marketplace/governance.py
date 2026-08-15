"""
Marketplace listing approval workflow and policy.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from .models import (
    ListingState,
    ProductCertification,
    ProductCertificationStatus,
    ProductListing,
    utcnow,
)


class ApprovalGate(str, Enum):
    """Constitutional certification gates a listing must satisfy (Phase 24.6 §10.4)."""

    PRODUCT_CERTIFICATION = "product_certification"
    LEARNING_PIPELINE_CERTIFICATION = "learning_pipeline_certification"
    SECURITY_CERTIFICATION = "security_certification"
    PRODUCTION_READINESS = "production_readiness"
    PAYMENT_COMPLIANCE = "payment_compliance"
    HUMAN_APPROVAL_FIRST_PUBLICATION = "human_approval_first_publication"
    QUALITY_SCORE = "quality_score"


class ApprovalGateResult(BaseModel):
    gate: str
    passed: bool
    reason: str = ""


class MarketplaceApprovalPolicy(BaseModel):
    """Policy for marketplace listing approval workflow."""

    require_product_certification: bool = True

    require_learning_pipeline_certified: bool = True

    require_human_approval_first_publication: bool = True

    min_quality_score: float = Field(default=0.6, ge=0.0, le=1.0)

    max_pending_approvals: int = Field(default=20, ge=0)

    auto_approve_after_approval: bool = False


class ListingApprovalDecision(BaseModel):
    listing_id: str
    gates: List[ApprovalGateResult] = Field(default_factory=list)
    approved: bool
    rejection_reason: Optional[str] = None
    decided_by: str = "system"
    decided_at: str = Field(default_factory=lambda: utcnow().isoformat())

    @property
    def passed_gates(self) -> List[ApprovalGateResult]:
        return [g for g in self.gates if g.passed]

    @property
    def failed_gates(self) -> List[ApprovalGateResult]:
        return [g for g in self.gates if not g.passed]


class MarketplaceApprovalEngine:
    """Evaluates the constitutional approval gates for a marketplace listing."""

    def __init__(self, policy: MarketplaceApprovalPolicy | None = None) -> None:
        self.policy = policy or MarketplaceApprovalPolicy()

    def evaluate(
        self,
        listing: ProductListing,
        product_certification: Optional[ProductCertification] = None,
        learning_pipeline_status: Optional[str] = None,
        human_approved: bool = False,
        first_publication: bool = False,
    ) -> ListingApprovalDecision:
        gates: List[ApprovalGateResult] = []

        gates.append(self._gate_product_certification(listing, product_certification))
        gates.append(
            self._gate_learning_pipeline(listing, learning_pipeline_status)
        )
        gates.append(self._gate_security_and_production(listing))
        gates.append(self._gate_payment_compliance(listing))
        gates.append(self._gate_quality_score(listing))
        gates.append(
            self._gate_human_approval(listing, human_approved, first_publication)
        )

        failed = [g for g in gates if not g.passed]
        approved = not failed
        rejection_reason = (
            "; ".join(g.reason for g in failed) if failed else None
        )

        return ListingApprovalDecision(
            listing_id=listing.listing_id,
            gates=gates,
            approved=approved,
            rejection_reason=rejection_reason,
        )

    # ------------------------------------------------------------------
    # Gate evaluators
    # ------------------------------------------------------------------

    def _gate_product_certification(
        self,
        listing: ProductListing,
        product_certification: Optional[ProductCertification],
    ) -> ApprovalGateResult:
        if not self.policy.require_product_certification:
            return ApprovalGateResult(
                gate=ApprovalGate.PRODUCT_CERTIFICATION,
                passed=True,
                reason="Product certification is not required by policy.",
            )

        if not listing.certification_id:
            return ApprovalGateResult(
                gate=ApprovalGate.PRODUCT_CERTIFICATION,
                passed=False,
                reason="Listing has no product certification attached.",
            )

        if not product_certification:
            return ApprovalGateResult(
                gate=ApprovalGate.PRODUCT_CERTIFICATION,
                passed=False,
                reason="Product certification record not provided.",
            )

        if product_certification.status != ProductCertificationStatus.PASSED:
            return ApprovalGateResult(
                gate=ApprovalGate.PRODUCT_CERTIFICATION,
                passed=False,
                reason=(
                    f"Product certification status is "
                    f"{product_certification.status.value}."
                ),
            )

        return ApprovalGateResult(
            gate=ApprovalGate.PRODUCT_CERTIFICATION,
            passed=True,
            reason="Product certification passed.",
        )

    def _gate_learning_pipeline(
        self, listing: ProductListing, learning_pipeline_status: Optional[str]
    ) -> ApprovalGateResult:
        if not self.policy.require_learning_pipeline_certified:
            return ApprovalGateResult(
                gate=ApprovalGate.LEARNING_PIPELINE_CERTIFICATION,
                passed=True,
                reason="Learning pipeline certification is not required by policy.",
            )

        allowed = {"CERTIFIED", "CONDITIONALLY_CERTIFIED"}

        if learning_pipeline_status not in allowed:
            return ApprovalGateResult(
                gate=ApprovalGate.LEARNING_PIPELINE_CERTIFICATION,
                passed=False,
                reason=(
                    "Learning pipeline is not certified "
                    f"(status={learning_pipeline_status})."
                ),
            )

        return ApprovalGateResult(
            gate=ApprovalGate.LEARNING_PIPELINE_CERTIFICATION,
            passed=True,
            reason=f"Learning pipeline is {learning_pipeline_status}.",
        )

    def _gate_security_and_production(self, listing: ProductListing) -> ApprovalGateResult:
        refs = [r.lower() for r in listing.evidence_refs]
        has_security = any("security" in r or "scan" in r for r in refs)
        has_production = any(
            "prod" in r or "production" in r or "runbook" in r for r in refs
        )
        missing = []
        if not has_security:
            missing.append("security certification")
        if not has_production:
            missing.append("production readiness")

        if missing:
            return ApprovalGateResult(
                gate="security_and_production_readiness",
                passed=False,
                reason=f"Missing evidence for: {', '.join(missing)}.",
            )
        return ApprovalGateResult(
            gate="security_and_production_readiness",
            passed=True,
            reason="Security and production-readiness evidence present.",
        )

    def _gate_payment_compliance(self, listing: ProductListing) -> ApprovalGateResult:
        if not listing.pricing:
            return ApprovalGateResult(
                gate=ApprovalGate.PAYMENT_COMPLIANCE,
                passed=False,
                reason="No pricing placement set; payment compliance unknown.",
            )
        return ApprovalGateResult(
            gate=ApprovalGate.PAYMENT_COMPLIANCE,
            passed=True,
            reason="Pricing placement defined; payment adapter available.",
        )

    def _gate_quality_score(self, listing: ProductListing) -> ApprovalGateResult:
        if listing.quality_score < self.policy.min_quality_score:
            return ApprovalGateResult(
                gate=ApprovalGate.QUALITY_SCORE,
                passed=False,
                reason=(
                    f"Quality score {listing.quality_score:.2f} is below minimum "
                    f"{self.policy.min_quality_score:.2f}."
                ),
            )
        return ApprovalGateResult(
            gate=ApprovalGate.QUALITY_SCORE,
            passed=True,
            reason=f"Quality score {listing.quality_score:.2f} meets minimum.",
        )

    def _gate_human_approval(
        self,
        listing: ProductListing,
        human_approved: bool,
        first_publication: bool,
    ) -> ApprovalGateResult:
        if not self.policy.require_human_approval_first_publication:
            return ApprovalGateResult(
                gate=ApprovalGate.HUMAN_APPROVAL_FIRST_PUBLICATION,
                passed=True,
                reason="Human first-publication approval is not required by policy.",
            )

        if not first_publication:
            return ApprovalGateResult(
                gate=ApprovalGate.HUMAN_APPROVAL_FIRST_PUBLICATION,
                passed=True,
                reason="Not a first-time publication.",
            )

        if human_approved:
            return ApprovalGateResult(
                gate=ApprovalGate.HUMAN_APPROVAL_FIRST_PUBLICATION,
                passed=True,
                reason="Human approval granted for first publication.",
            )

        return ApprovalGateResult(
            gate=ApprovalGate.HUMAN_APPROVAL_FIRST_PUBLICATION,
            passed=False,
            reason="Human approval required for first publication.",
        )
