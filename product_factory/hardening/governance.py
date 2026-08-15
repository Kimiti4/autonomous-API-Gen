"""
Phase 24.1 — Product Governance and Launch Approval Hardening.
"""

from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, Field

from ..utils import deterministic_id, utcnow
from .models import (
    ApprovalStatus,
    GovernanceGateResult,
    ProductAction,
    ProductApprovalRequest,
    ProductEvidenceContext,
    ProductGate,
    ProductGovernanceDecision,
)


class ProductGovernancePolicy(BaseModel):
    """Policy controlling product governance gates."""

    require_market_evidence: bool = True

    require_security_review: bool = True

    require_pricing_plan: bool = True

    require_deployment_plan: bool = True

    require_revenue_simulation: bool = True

    require_launch_approval: bool = True


class ProductGovernanceEngine:
    """Engine enforcing product governance gates."""

    def __init__(
        self,
        policy: ProductGovernancePolicy | None = None,
    ) -> None:
        self.policy = policy or ProductGovernancePolicy()
        self.approvals: Dict[str, ProductApprovalRequest] = {}

    def evaluate_action(
        self,
        product_id: str,
        action: ProductAction,
        context: ProductEvidenceContext,
    ) -> ProductGovernanceDecision:
        action = ProductAction(action)

        gates: List[GovernanceGateResult] = []
        blockers: List[str] = []

        def add_gate(
            gate: ProductGate,
            passed: bool,
            issues: List[str] | None = None,
            evidence_refs: List[str] | None = None,
        ) -> None:
            gates.append(
                GovernanceGateResult(
                    gate=gate,
                    passed=passed,
                    issues=issues or [],
                    evidence_refs=evidence_refs or [],
                )
            )

            if not passed:
                blockers.append(gate.value)

        if action in {ProductAction.LAUNCH, ProductAction.DEPLOY}:
            add_gate(
                ProductGate.MARKET_EVIDENCE,
                context.has_market_research,
                [] if context.has_market_research else ["Market evidence missing."],
            )

            security_passed = (
                context.has_security_review
                and context.critical_findings == 0
            )

            add_gate(
                ProductGate.SECURITY,
                security_passed,
                []
                if security_passed
                else [
                    "Security review missing or critical security findings open."
                ],
            )

            add_gate(
                ProductGate.PRICING,
                context.has_pricing_plan,
                [] if context.has_pricing_plan else ["Pricing plan missing."],
            )

            add_gate(
                ProductGate.DEPLOYMENT,
                context.has_deployment_plan,
                [] if context.has_deployment_plan else ["Deployment plan missing."],
            )

            add_gate(
                ProductGate.REVENUE_SIMULATION,
                context.has_revenue_simulation,
                []
                if context.has_revenue_simulation
                else ["Revenue simulation missing."],
            )

        if action == ProductAction.PRICE_CHANGE:
            add_gate(
                ProductGate.PRICING,
                context.has_pricing_plan,
                [] if context.has_pricing_plan else ["Pricing plan missing."],
            )

        if action == ProductAction.MARKETING_PUBLISH:
            add_gate(
                ProductGate.MARKET_EVIDENCE,
                context.has_market_research,
                [] if context.has_market_research else ["Market evidence missing."],
            )

        approval_required = (
            self.policy.require_launch_approval
            and action
            in {
                ProductAction.LAUNCH,
                ProductAction.DEPLOY,
                ProductAction.PRICE_CHANGE,
                ProductAction.MARKETING_PUBLISH,
            }
        )

        required_approvals: List[str] = []

        if approval_required:
            approval_passed = bool(context.approval_refs)

            add_gate(
                ProductGate.GOVERNANCE_APPROVAL,
                approval_passed,
                []
                if approval_passed
                else ["Governance approval references missing."],
                context.approval_refs,
            )

            if not approval_passed:
                required_approvals.append("product_governance_approval")

        allowed = len(blockers) == 0

        return ProductGovernanceDecision(
            product_id=product_id,
            action=action,
            allowed=allowed,
            blockers=blockers,
            gates=gates,
            required_approvals=required_approvals,
            timestamp=utcnow().isoformat(),
        )

    def submit_approval(
        self,
        product_id: str,
        action: ProductAction,
        requested_by: str,
        evidence_refs: List[str] | None = None,
    ) -> ProductApprovalRequest:
        created_at = utcnow().isoformat()

        approval_id = deterministic_id(
            "product_approval_request",
            {
                "product_id": product_id,
                "action": ProductAction(action).value,
                "requested_by": requested_by,
                "created_at": created_at,
            },
        )

        approval = ProductApprovalRequest(
            id=approval_id,
            product_id=product_id,
            action=ProductAction(action),
            requested_by=requested_by,
            evidence_refs=evidence_refs or [],
            status=ApprovalStatus.PENDING,
            created_at=created_at,
        )

        self.approvals[approval_id] = approval

        return approval

    def decide_approval(
        self,
        approval_id: str,
        decided_by: str,
        approved: bool,
        comments: str = "",
    ) -> ProductApprovalRequest:
        approval = self.approvals.get(approval_id)

        if not approval:
            raise KeyError(f"Approval request not found: {approval_id}")

        approval.status = (
            ApprovalStatus.APPROVED
            if approved
            else ApprovalStatus.REJECTED
        )

        approval.decided_at = utcnow().isoformat()
        approval.decided_by = decided_by
        approval.comments = comments

        return approval
