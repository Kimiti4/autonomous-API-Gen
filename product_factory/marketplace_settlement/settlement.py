"""
Settlement engine.
"""

from __future__ import annotations

from typing import Dict, List

from .gateway import GovernanceGateway, SettlementAdapter
from .ledger import FinancialLedgerEngine
from .models import (
    LedgerEntry,
    LedgerEntryType,
    PayoutInstruction,
    SettlementBatch,
    SettlementPolicy,
    SettlementStatus,
)
from .reconciliation import ReconciliationEngine


class SettlementEngine:
    """Creates, approves, and executes settlement batches."""

    def __init__(
        self,
        ledger: FinancialLedgerEngine,
        reconciliation: ReconciliationEngine,
        governance_gateway: GovernanceGateway | None = None,
        settlement_adapter: SettlementAdapter | None = None,
        policy: SettlementPolicy | None = None,
    ) -> None:
        self.ledger = ledger
        self.reconciliation = reconciliation
        self.governance_gateway = governance_gateway
        self.settlement_adapter = settlement_adapter
        self.policy = policy or SettlementPolicy()

        self.batches: Dict[str, SettlementBatch] = {}
        self.payouts: List[PayoutInstruction] = []

        self.settled_entry_ids: set[str] = set()

    def create_batch(
        self,
        marketplace_id: str,
        tenant_id: str,
        currency: str,
        period_start,
        period_end,
        actor_id: str,
    ) -> SettlementBatch:
        entries = self.ledger.entries_for_period(
            marketplace_id=marketplace_id,
            period_start=period_start,
            period_end=period_end,
            tenant_id=tenant_id,
        )

        entries = [
            entry
            for entry in entries
            if entry.id not in self.settled_entry_ids
            and entry.currency == currency
        ]

        if not entries:
            raise ValueError("No unsettled ledger entries found for period.")

        if len(entries) > self.policy.max_batch_entries:
            raise ValueError("Settlement batch exceeds maximum entry count.")

        gross_amount = 0.0
        refund_amount = 0.0
        fee_amount = 0.0
        tax_amount = 0.0
        net_amount = 0.0

        for entry in entries:
            net_amount += entry.amount

            if entry.entry_type == LedgerEntryType.CREDIT:
                gross_amount += entry.amount

            if entry.entry_type == LedgerEntryType.DEBIT:
                refund_amount += abs(entry.amount)

            if entry.entry_type == LedgerEntryType.FEE:
                fee_amount += abs(entry.amount)

            if entry.entry_type == LedgerEntryType.TAX:
                tax_amount += abs(entry.amount)

        net_amount = round(net_amount, 2)

        if net_amount < self.policy.min_settlement_amount:
            raise ValueError("Settlement amount is below minimum threshold.")

        if net_amount < 0 and not self.policy.allow_negative_settlement:
            status = SettlementStatus.FAILED
        else:
            status = SettlementStatus.DRAFT

        batch = SettlementBatch(
            marketplace_id=marketplace_id,
            tenant_id=tenant_id,
            currency=currency,
            period_start=period_start,
            period_end=period_end,
            gross_amount=round(gross_amount, 2),
            refund_amount=round(refund_amount, 2),
            fee_amount=round(fee_amount, 2),
            tax_amount=round(tax_amount, 2),
            net_amount=net_amount,
            entry_ids=[entry.id for entry in entries],
            status=status,
        )

        self.batches[batch.id] = batch

        return batch

    def approve_settlement(
        self,
        batch_id: str,
        actor_id: str,
        approval_ref: str | None = None,
    ) -> SettlementBatch:
        batch = self.get_batch(batch_id)

        if batch.status not in {
            SettlementStatus.DRAFT,
            SettlementStatus.PENDING_GOVERNANCE,
        }:
            raise ValueError("Settlement batch cannot be approved.")

        if self.policy.require_governance_for_settlement:
            if not self.governance_gateway:
                raise PermissionError(
                    "Governance gateway is required for settlement approval."
                )

            decision = self.governance_gateway.evaluate_action(
                action="MARKETPLACE_SETTLEMENT_APPROVAL",
                context={
                    "batch_id": batch.id,
                    "marketplace_id": batch.marketplace_id,
                    "tenant_id": batch.tenant_id,
                    "net_amount": batch.net_amount,
                    "currency": batch.currency,
                    "actor_id": actor_id,
                },
            )

            if decision.decision == "DENY":
                batch.status = SettlementStatus.FAILED
                raise PermissionError(
                    f"Settlement approval denied: {decision.reason}"
                )

            if decision.decision == "REQUIRE_APPROVAL":
                batch.status = SettlementStatus.PENDING_GOVERNANCE
                batch.governance_ref = decision.approval_ref
                return batch

            batch.governance_ref = decision.approval_ref or approval_ref

        batch.status = SettlementStatus.APPROVED

        return batch

    def execute_settlement(
        self,
        batch_id: str,
        actor_id: str,
    ) -> SettlementBatch:
        batch = self.get_batch(batch_id)

        if batch.status != SettlementStatus.APPROVED:
            raise ValueError("Settlement batch must be approved before execution.")

        if self.reconciliation.has_blocking_mismatches(batch.marketplace_id):
            raise PermissionError(
                "Settlement blocked by unresolved reconciliation mismatches."
            )

        latest_report = self.reconciliation.latest_report(batch.marketplace_id)

        if latest_report and latest_report.status.value == "FAIL":
            raise PermissionError(
                "Settlement blocked because latest reconciliation failed."
            )

        if not self.settlement_adapter:
            raise PermissionError("Settlement adapter is not configured.")

        batch.status = SettlementStatus.SETTLING

        try:
            provider_ref = self.settlement_adapter.execute_settlement(batch)
        except Exception as exc:
            batch.status = SettlementStatus.FAILED
            raise RuntimeError(f"Settlement execution failed: {exc}") from exc

        if batch.net_amount != 0:
            settlement_entry = LedgerEntry(
                event_id=batch.id,
                idempotency_key=f"settlement:{batch.id}",
                entry_type=LedgerEntryType.SETTLEMENT,
                marketplace_id=batch.marketplace_id,
                tenant_id=batch.tenant_id,
                amount=-batch.net_amount,
                currency=batch.currency,
            )

            self.ledger.append_entry(settlement_entry)

            self.settled_entry_ids.update(batch.entry_ids)

        payout = PayoutInstruction(
            settlement_batch_id=batch.id,
            participant_id=batch.tenant_id,
            amount=batch.net_amount,
            currency=batch.currency,
            status="COMPLETED",
            provider_ref=provider_ref,
        )

        self.payouts.append(payout)

        batch.provider_ref = provider_ref
        batch.status = SettlementStatus.SETTLED
        batch.executed_at = batch.executed_at or batch.created_at

        return batch

    def get_batch(self, batch_id: str) -> SettlementBatch:
        batch = self.batches.get(batch_id)

        if not batch:
            raise KeyError(f"Settlement batch not found: {batch_id}")

        return batch
