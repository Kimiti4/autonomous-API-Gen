"""
Financial reconciliation engine.

Detects mismatches between payment events and ledger entries, including
refund-without-original-payment, refund-exceeds-captured, duplicate
idempotency keys, and tax/fee mismatches. Severe mismatches are escalated
to the Phase 28 Governance Kernel.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .ledger import FinancialLedgerEngine
from .models import (
    GovernanceAction,
    LedgerEntryType,
    PaymentStatus,
    ReconciliationMismatch,
    ReconciliationMismatchKind,
    ReconciliationReport,
    ReconciliationSeverity,
    ReconciliationStatus,
    utcnow,
)


class ReconciliationEngine:
    """Reconciles marketplace payment events against the financial ledger."""

    def __init__(
        self,
        ledger: FinancialLedgerEngine,
        payment_engine,
        tax_engine=None,
        policy=None,
        governance=None,
    ) -> None:
        self.ledger = ledger
        self.payment_engine = payment_engine
        self.tax_engine = tax_engine
        self.policy = policy
        self.governance = governance

        self._reports: Dict[str, ReconciliationReport] = {}

    def run_reconciliation(
        self,
        marketplace_id: Optional[str] = None,
    ) -> ReconciliationReport:
        events = self.payment_engine.processed_events()

        if marketplace_id:
            events = [e for e in events if e.marketplace_id == marketplace_id]

        entries = self.ledger.report(marketplace_id)

        mismatches: List[ReconciliationMismatch] = []

        payment_event_ids = {e.event_id for e in events}

        ledger_payment_entries: Dict[str, FinancialLedgerEntry] = {}

        for entry in entries:
            if not entry.source_event_id:
                continue

            if entry.entry_type in (
                LedgerEntryType.PAYMENT_CAPTURED,
                LedgerEntryType.PAYMENT_FAILED,
            ):
                ledger_payment_entries.setdefault(entry.source_event_id, entry)

        processed_event_ids = set()

        for event in events:
            if event.status in (
                PaymentStatus.CAPTURED,
                PaymentStatus.AUTHORIZED,
                PaymentStatus.FAILED,
                PaymentStatus.CANCELLED,
            ):
                processed_event_ids.add(event.event_id)

                entry = ledger_payment_entries.get(event.event_id)

                if not entry:
                    mismatches.append(
                        ReconciliationMismatch(
                            marketplace_id=event.marketplace_id,
                            order_id=event.order_id,
                            kind=ReconciliationMismatchKind.PAYMENT_EVENT_MISSING_LEDGER,
                            severity=ReconciliationSeverity.HIGH,
                            details=(
                                f"Payment event {event.event_id} has no "
                                "corresponding ledger entry."
                            ),
                            evidence_refs=(
                                [event.evidence_ref] if event.evidence_ref else []
                            ),
                        )
                    )

                    continue

                if abs(entry.amount - event.amount) > 0.0001:
                    mismatches.append(
                        ReconciliationMismatch(
                            marketplace_id=event.marketplace_id,
                            order_id=event.order_id,
                            kind=ReconciliationMismatchKind.AMOUNT_MISMATCH,
                            severity=ReconciliationSeverity.MEDIUM,
                            details=(
                                f"Amount mismatch for {event.event_id}: "
                                f"event={event.amount}, ledger={entry.amount}."
                            ),
                            evidence_refs=[event.evidence_ref]
                            if event.evidence_ref
                            else [],
                        )
                    )

                if entry.currency != event.currency:
                    mismatches.append(
                        ReconciliationMismatch(
                            marketplace_id=event.marketplace_id,
                            order_id=event.order_id,
                            kind=ReconciliationMismatchKind.CURRENCY_MISMATCH,
                            severity=ReconciliationSeverity.LOW,
                            details=(
                                f"Currency mismatch for {event.event_id}: "
                                f"event={event.currency}, ledger={entry.currency}."
                            ),
                        )
                    )

                if entry.status != event.status.value:
                    mismatches.append(
                        ReconciliationMismatch(
                            marketplace_id=event.marketplace_id,
                            order_id=event.order_id,
                            kind=ReconciliationMismatchKind.STATUS_MISMATCH,
                            severity=ReconciliationSeverity.MEDIUM,
                            details=(
                                f"Status mismatch for {event.event_id}: "
                                f"event={event.status.value}, ledger={entry.status}."
                            ),
                        )
                    )

        for source_id, entry in ledger_payment_entries.items():
            if source_id not in payment_event_ids:
                mismatches.append(
                    ReconciliationMismatch(
                        marketplace_id=entry.marketplace_id,
                        order_id=entry.order_id,
                        kind=ReconciliationMismatchKind.LEDGER_MISSING_PAYMENT_EVENT,
                        severity=ReconciliationSeverity.MEDIUM,
                        details=(
                            f"Ledger entry {entry.ledger_id} references missing "
                            f"payment event {source_id}."
                        ),
                        evidence_refs=[entry.evidence_ref] if entry.evidence_ref else [],
                    )
                )

        for duplicate_key in self.ledger.duplicate_idempotency_keys():
            mismatches.append(
                ReconciliationMismatch(
                    marketplace_id=marketplace_id or "",
                    kind=ReconciliationMismatchKind.DUPLICATE_IDEMPOTENCY_KEY,
                    severity=ReconciliationSeverity.CRITICAL,
                    details=f"Duplicate idempotency key in ledger: {duplicate_key}.",
                    evidence_refs=[duplicate_key],
                )
            )

        captured_by_order: Dict[str, float] = {}
        refunded_by_order: Dict[str, float] = {}

        for entry in entries:
            if not entry.order_id:
                continue

            if entry.entry_type == LedgerEntryType.PAYMENT_CAPTURED:
                captured_by_order[entry.order_id] = (
                    captured_by_order.get(entry.order_id, 0.0) + entry.amount
                )

            if entry.entry_type in (LedgerEntryType.REFUND_APPROVED, LedgerEntryType.REFUND_COMPLETED):
                refunded_by_order[entry.order_id] = (
                    refunded_by_order.get(entry.order_id, 0.0) + entry.amount
                )

            if (
                entry.entry_type in (LedgerEntryType.REFUND_APPROVED, LedgerEntryType.REFUND_COMPLETED)
                and entry.source_event_id
                and entry.source_event_id not in processed_event_ids
            ):
                mismatches.append(
                    ReconciliationMismatch(
                        marketplace_id=entry.marketplace_id,
                        order_id=entry.order_id,
                        kind=ReconciliationMismatchKind.REFUND_WITHOUT_ORIGINAL_PAYMENT,
                        severity=ReconciliationSeverity.HIGH,
                        details=(
                            f"Refund ledger entry {entry.ledger_id} references a "
                            "payment event that was not captured."
                        ),
                    )
                )

        for order_id, refunded in refunded_by_order.items():
            captured = captured_by_order.get(order_id, 0.0)

            if refunded > captured + 0.0001:
                mismatches.append(
                    ReconciliationMismatch(
                        marketplace_id=marketplace_id or "",
                        order_id=order_id,
                        kind=ReconciliationMismatchKind.REFUND_EXCEEDS_CAPTURED,
                        severity=ReconciliationSeverity.HIGH,
                        details=(
                            f"Refunded amount {refunded} exceeds captured "
                            f"amount {captured} for order {order_id}."
                        ),
                    )
                )

        if self.tax_engine:
            tax_calc_ids = {
                getattr(c, "tax_request_id", None)
                for c in self.tax_engine.recent_calculations()
            }

            for entry in entries:
                if (
                    entry.entry_type == LedgerEntryType.TAX_CALCULATED
                    and entry.source_event_id not in tax_calc_ids
                ):
                    mismatches.append(
                        ReconciliationMismatch(
                            marketplace_id=entry.marketplace_id,
                            order_id=entry.order_id,
                            kind=ReconciliationMismatchKind.TAX_MISMATCH,
                            severity=ReconciliationSeverity.MEDIUM,
                            details=(
                                f"Tax ledger entry {entry.ledger_id} has no "
                                "corresponding tax calculation."
                            ),
                        )
                    )

        summary: Dict[str, int] = {}

        for mismatch in mismatches:
            summary[mismatch.kind.value] = (
                summary.get(mismatch.kind.value, 0) + 1
            )

        severe = any(
            m.severity in (ReconciliationSeverity.HIGH, ReconciliationSeverity.CRITICAL)
            for m in mismatches
        )

        status = (
            ReconciliationStatus.HEALTHY
            if not mismatches
            else ReconciliationStatus.MISMATCHES_DETECTED
        )

        governance_ref: Optional[str] = None

        if severe and self.governance:
            decision = self.governance.evaluate(
                action=GovernanceAction.FINANCIAL_ROLLBACK,
                actor="reconciliation",
                context={
                    "mismatch_count": len(mismatches),
                    "severe": True,
                },
                evidence_refs=[m.mismatch_id for m in mismatches],
            )

            governance_ref = decision.audit_ref

            if not decision.allowed:
                status = ReconciliationStatus.FAILED

        report = ReconciliationReport(
            marketplace_id=marketplace_id or "",
            total_entries=len(entries),
            mismatch_count=len(mismatches),
            mismatches=mismatches,
            summary=summary,
            governance_ref=governance_ref,
            status=status,
        )

        self._reports[report.report_id] = report

        return report

    def latest_report(self) -> Optional[ReconciliationReport]:
        if not self._reports:
            return None

        return list(self._reports.values())[-1]
