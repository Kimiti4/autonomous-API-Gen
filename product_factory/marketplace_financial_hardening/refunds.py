"""
Refund governance engine.

Refunds below threshold may be auto-approved; refunds above threshold require
governance approval. All refunds produce idempotent ledger entries.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .ledger import FinancialLedgerEngine
from .models import (
    FinancialAuditEvent,
    FinancialLedgerEntry,
    GovernanceAction,
    GovernanceDecision,
    LedgerEntryType,
    MarketplaceFinancialPolicy,
    RefundRequest,
    RefundStatus,
    utcnow,
)


def _governance_decision(
    governance,
    action: GovernanceAction,
    actor: str,
    evidence_refs: List[str],
    context: Dict,
) -> GovernanceDecision:
    if governance is None:
        return GovernanceDecision(
            action=action,
            actor=actor,
            allowed=True,
            decision="APPROVED",
        )

    return governance.evaluate(
        action=action,
        actor=actor,
        context=context,
        evidence_refs=evidence_refs,
    )


class RefundGovernanceEngine:
    """Creates and governs refund requests under marketplace policy."""

    def __init__(
        self,
        ledger: Optional[FinancialLedgerEngine] = None,
        policy: Optional[MarketplaceFinancialPolicy] = None,
        governance=None,
    ) -> None:
        self.ledger = ledger
        self.policy = policy or MarketplaceFinancialPolicy()
        self.governance = governance

        self._refunds: Dict[str, RefundRequest] = {}
        self._by_idempotency: Dict[str, RefundRequest] = {}
        self.audit_events: List[FinancialAuditEvent] = []

    def request_refund(
        self,
        marketplace_id: str,
        order_id: str,
        listing_id: str,
        tenant_id: str,
        amount: float,
        currency: str,
        requested_by: str,
        original_payment_event_id: Optional[str] = None,
        reason_code: str = "",
        reason: str = "",
        idempotency_key: Optional[str] = None,
    ) -> RefundRequest:
        if idempotency_key and idempotency_key in self._by_idempotency:
            return self._by_idempotency[idempotency_key]

        above_threshold = (
            currency == self.policy.auto_approve_refund_threshold_currency
            and amount > self.policy.auto_approve_refund_threshold_amount
        )

        refund = RefundRequest(
            marketplace_id=marketplace_id,
            order_id=order_id,
            listing_id=listing_id,
            tenant_id=tenant_id,
            amount=amount,
            currency=currency,
            original_payment_event_id=original_payment_event_id,
            reason_code=reason_code,
            reason=reason,
            requested_by=requested_by,
            idempotency_key=idempotency_key,
        )

        self._store(refund)

        self._append_ledger_entry(
            LedgerEntryType.REFUND_REQUESTED,
            refund,
            idempotency_key=f"refreq_{refund.refund_id}",
        )

        if (
            not above_threshold
            and self.policy.auto_approve_small_refunds
        ):
            decision = _governance_decision(
                self.governance,
                GovernanceAction.REFUND_ABOVE_THRESHOLD,
                requested_by,
                [refund.refund_id],
                {"refund_id": refund.refund_id, "amount": amount, "currency": currency},
            )

            if decision.allowed:
                refund.status = RefundStatus.APPROVED
                refund.approval_ref = (
                    getattr(decision, "approval_ref", None)
                    or f"auto:{requested_by}"
                )
                refund.governance_ref = getattr(decision, "audit_ref", None)
                refund.updated_at = utcnow()

                self._append_ledger_entry(
                    LedgerEntryType.REFUND_APPROVED,
                    refund,
                    idempotency_key=f"refapp_{refund.refund_id}",
                )

                refund.status = RefundStatus.COMPLETED
                refund.completed_at = utcnow()
                refund.updated_at = utcnow()

                self._append_ledger_entry(
                    LedgerEntryType.REFUND_COMPLETED,
                    refund,
                    idempotency_key=f"refcomp_{refund.refund_id}",
                )

                self._audit(
                    action="refund_auto_completed",
                    marketplace_id=marketplace_id,
                    actor=requested_by,
                    status="OK",
                    amount=amount,
                    currency=currency,
                    governance_ref=decision.audit_ref,
                    evidence_ref=refund.refund_id,
                )
        elif above_threshold:
            decision = _governance_decision(
                self.governance,
                GovernanceAction.REFUND_ABOVE_THRESHOLD,
                requested_by,
                [refund.refund_id, original_payment_event_id],
                {
                    "refund_id": refund.refund_id,
                    "amount": amount,
                    "currency": currency,
                    "order_id": order_id,
                },
            )

            refund.governance_ref = decision.audit_ref

            if not decision.allowed:
                refund.status = RefundStatus.REJECTED
                refund.updated_at = utcnow()

                self._audit(
                    action="refund_above_threshold_denied",
                    marketplace_id=marketplace_id,
                    actor=requested_by,
                    status="DENIED",
                    amount=amount,
                    currency=currency,
                    governance_ref=decision.audit_ref,
                    evidence_ref=refund.refund_id,
                    reason="Governance denied refund above threshold.",
                )

                raise ValueError(
                    "Refund above threshold requires governance approval, "
                    "which was denied."
                )

            refund.status = RefundStatus.PENDING_APPROVAL
            refund.governance_ref = getattr(decision, "audit_ref", None)
            refund.updated_at = utcnow()

            self._audit(
                action="refund_above_threshold_pending_approval",
                marketplace_id=marketplace_id,
                actor=requested_by,
                status="PENDING",
                amount=amount,
                currency=currency,
                governance_ref=decision.audit_ref,
                evidence_ref=refund.refund_id,
            )
        else:
            refund.status = RefundStatus.PENDING_APPROVAL
            refund.updated_at = utcnow()

            self._audit(
                action="refund_requested_pending_approval",
                marketplace_id=marketplace_id,
                actor=requested_by,
                status="PENDING",
                amount=amount,
                currency=currency,
                evidence_ref=refund.refund_id,
            )

        return refund

    def approve_refund(
        self,
        refund_id: str,
        approver_id: str,
        approval_ref: Optional[str] = None,
    ) -> RefundRequest:
        refund = self._refunds.get(refund_id)

        if not refund:
            raise KeyError(f"Refund request not found: {refund_id}")

        if refund.status != RefundStatus.PENDING_APPROVAL:
            raise ValueError("Refund must be pending approval to approve.")

        if self.policy.require_governance_for_refund_above_threshold:
            decision = _governance_decision(
                self.governance,
                GovernanceAction.REFUND_ABOVE_THRESHOLD,
                approver_id,
                [refund.refund_id],
                {"refund_id": refund_id, "amount": refund.amount},
            )

            if not decision.allowed:
                refund.status = RefundStatus.REJECTED
                refund.updated_at = utcnow()

                self._audit(
                    action="refund_approval_denied",
                    marketplace_id=refund.marketplace_id,
                    actor=approver_id,
                    status="DENIED",
                    amount=refund.amount,
                    currency=refund.currency,
                    governance_ref=decision.audit_ref,
                    evidence_ref=refund_id,
                    reason="Governance denied refund approval.",
                )

                raise ValueError("Refund approval denied by governance.")

            refund.governance_ref = decision.audit_ref

        refund.status = RefundStatus.APPROVED
        refund.approval_ref = approval_ref or f"approval:{approver_id}"
        refund.updated_at = utcnow()

        self._append_ledger_entry(
            LedgerEntryType.REFUND_APPROVED,
            refund,
            idempotency_key=f"refapp_{refund.refund_id}",
        )

        refund.status = RefundStatus.COMPLETED
        refund.completed_at = utcnow()
        refund.updated_at = utcnow()

        self._append_ledger_entry(
            LedgerEntryType.REFUND_COMPLETED,
            refund,
            idempotency_key=f"refcomp_{refund.refund_id}",
        )

        self._audit(
            action="refund_completed",
            marketplace_id=refund.marketplace_id,
            actor=approver_id,
            status="OK",
            amount=refund.amount,
            currency=refund.currency,
            evidence_ref=refund.refund_id,
        )

        return refund

    def reject_refund(
        self,
        refund_id: str,
        approver_id: str,
        reason: str = "",
    ) -> RefundRequest:
        refund = self._refunds.get(refund_id)

        if not refund:
            raise KeyError(f"Refund request not found: {refund_id}")

        if refund.status != RefundStatus.PENDING_APPROVAL:
            raise ValueError("Refund must be pending approval to reject.")

        refund.status = RefundStatus.REJECTED
        refund.reason = reason
        refund.updated_at = utcnow()

        self._audit(
            action="refund_rejected",
            marketplace_id=refund.marketplace_id,
            actor=approver_id,
            status="REJECTED",
            amount=refund.amount,
            currency=refund.currency,
            evidence_ref=refund_id,
            reason=reason,
        )

        return refund

    def refund(self, refund_id: str) -> RefundRequest:
        refund = self._refunds.get(refund_id)

        if not refund:
            raise KeyError(f"Refund request not found: {refund_id}")

        return refund

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _store(self, refund: RefundRequest) -> None:
        self._refunds[refund.refund_id] = refund

        if refund.idempotency_key:
            self._by_idempotency[refund.idempotency_key] = refund

    def _append_ledger_entry(
        self,
        entry_type: LedgerEntryType,
        refund: RefundRequest,
        idempotency_key: str,
    ) -> None:
        if not self.ledger:
            return

        self.ledger.append(
            FinancialLedgerEntry(
                marketplace_id=refund.marketplace_id,
                order_id=refund.order_id,
                listing_id=refund.listing_id,
                tenant_id=refund.tenant_id,
                entry_type=entry_type,
                amount=refund.amount,
                currency=refund.currency,
                status=entry_type.value,
                idempotency_key=idempotency_key,
                source_event_id=refund.original_payment_event_id,
                evidence_ref=refund.refund_id,
            )
        )

    def _audit(self, **kwargs) -> FinancialAuditEvent:
        event = FinancialAuditEvent(**kwargs)

        if self.ledger:
            self.ledger.record_audit(event)
        else:
            self.audit_events.append(event)

        return event
