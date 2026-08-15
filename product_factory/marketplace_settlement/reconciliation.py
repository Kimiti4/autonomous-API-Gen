"""
Financial reconciliation engine.
"""

from __future__ import annotations

from typing import Dict, List

from .ledger import FinancialLedgerEngine
from .models import (
    FinancialEventType,
    MismatchStatus,
    ReconciliationMismatch,
    ReconciliationReport,
    ReconciliationStatus,
    SettlementPolicy,
)


LEDGER_REQUIRED_EVENTS = {
    FinancialEventType.PAYMENT_CAPTURED,
    FinancialEventType.REFUND_ISSUED,
    FinancialEventType.FEE_CHARGED,
    FinancialEventType.TAX_CHARGED,
    FinancialEventType.CHARGEBACK_OPENED,
    FinancialEventType.ADJUSTMENT,
    FinancialEventType.PAYOUT_COMPLETED,
}


class ReconciliationEngine:
    """Reconciles financial events against ledger entries."""

    def __init__(
        self,
        ledger: FinancialLedgerEngine,
        policy: SettlementPolicy,
    ) -> None:
        self.ledger = ledger
        self.policy = policy

        self.mismatches: Dict[str, ReconciliationMismatch] = {}
        self.reports: List[ReconciliationReport] = []

    def run(
        self,
        marketplace_id: str,
        period_start,
        period_end,
    ) -> ReconciliationReport:
        new_mismatches: List[ReconciliationMismatch] = []

        entries = self.ledger.entries_for_period(
            marketplace_id=marketplace_id,
            period_start=period_start,
            period_end=period_end,
        )

        events = [
            event
            for event in self.ledger.events
            if event.marketplace_id == marketplace_id
            and period_start <= event.occurred_at <= period_end
        ]

        event_ids = {event.id for event in events}
        ledger_event_ids = {entry.event_id for entry in entries if entry.event_id}

        for event in events:
            if event.event_type in LEDGER_REQUIRED_EVENTS:
                if event.id not in ledger_event_ids:
                    new_mismatches.append(
                        self._build_mismatch(
                            marketplace_id=marketplace_id,
                            mismatch_type="MISSING_LEDGER_ENTRY",
                            severity="HIGH",
                            entity_id=event.id,
                            expected="ledger_entry",
                            observed="missing",
                            details={
                                "event_type": event.event_type.value,
                                "idempotency_key": event.idempotency_key,
                            },
                        )
                    )

        for entry in entries:
            if entry.event_id and entry.event_id not in event_ids:
                new_mismatches.append(
                    self._build_mismatch(
                        marketplace_id=marketplace_id,
                        mismatch_type="ORPHAN_LEDGER_ENTRY",
                        severity="HIGH",
                        entity_id=entry.id,
                        expected="financial_event",
                        observed="missing",
                        details={
                            "entry_type": entry.entry_type.value,
                            "idempotency_key": entry.idempotency_key,
                        },
                    )
                )

        balances = self._balances_by_tenant(marketplace_id)

        for (tenant_id, currency), balance in balances.items():
            if balance < 0 and not self.policy.allow_negative_balances:
                new_mismatches.append(
                    self._build_mismatch(
                        marketplace_id=marketplace_id,
                        mismatch_type="NEGATIVE_BALANCE",
                        severity="HIGH",
                        entity_id=f"{tenant_id}:{currency}",
                        expected=">=0",
                        observed=str(balance),
                        details={
                            "tenant_id": tenant_id,
                            "currency": currency,
                        },
                    )
                )

        for mismatch in new_mismatches:
            if mismatch.id not in self.mismatches:
                self.mismatches[mismatch.id] = mismatch

        open_mismatches = [
            mismatch
            for mismatch in self.mismatches.values()
            if mismatch.marketplace_id == marketplace_id
            and mismatch.status == MismatchStatus.OPEN
        ]

        high_mismatches = [
            mismatch
            for mismatch in open_mismatches
            if mismatch.severity == "HIGH"
        ]

        warning_mismatches = [
            mismatch
            for mismatch in open_mismatches
            if mismatch.severity == "WARNING"
        ]

        if high_mismatches:
            status = ReconciliationStatus.FAIL
        elif warning_mismatches:
            status = ReconciliationStatus.WARN
        else:
            status = ReconciliationStatus.OK

        report = ReconciliationReport(
            marketplace_id=marketplace_id,
            period_start=period_start,
            period_end=period_end,
            status=status,
            mismatches=open_mismatches,
        )

        self.reports.append(report)

        return report

    def resolve_mismatch(
        self,
        mismatch_id: str,
        actor_id: str,
        notes: str = "",
    ) -> ReconciliationMismatch:
        mismatch = self.mismatches.get(mismatch_id)

        if not mismatch:
            raise KeyError(f"Mismatch not found: {mismatch_id}")

        mismatch.status = MismatchStatus.RESOLVED
        mismatch.resolved_by = actor_id
        mismatch.details["resolution_notes"] = notes

        return mismatch

    def latest_report(self, marketplace_id: str) -> ReconciliationReport | None:
        for report in reversed(self.reports):
            if report.marketplace_id == marketplace_id:
                return report

        return None

    def has_blocking_mismatches(self, marketplace_id: str) -> bool:
        return any(
            mismatch.marketplace_id == marketplace_id
            and mismatch.status == MismatchStatus.OPEN
            and mismatch.severity == "HIGH"
            for mismatch in self.mismatches.values()
        )

    def _build_mismatch(
        self,
        marketplace_id: str,
        mismatch_type: str,
        severity: str,
        entity_id: str | None,
        expected: str,
        observed: str,
        details: Dict,
    ) -> ReconciliationMismatch:
        mismatch_id = (
            f"mismatch:{marketplace_id}:{mismatch_type}:{entity_id or 'unknown'}"
        )

        return ReconciliationMismatch(
            id=mismatch_id,
            marketplace_id=marketplace_id,
            mismatch_type=mismatch_type,
            severity=severity,
            entity_id=entity_id,
            expected=expected,
            observed=observed,
            details=details,
        )

    def _balances_by_tenant(self, marketplace_id: str) -> Dict[tuple[str, str], float]:
        balances: Dict[tuple[str, str], float] = {}

        for entry in self.ledger.entries:
            if entry.marketplace_id != marketplace_id:
                continue

            key = (entry.tenant_id, entry.currency)

            balances[key] = round(balances.get(key, 0.0) + entry.amount, 2)

        return balances
