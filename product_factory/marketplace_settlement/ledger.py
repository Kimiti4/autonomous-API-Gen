"""
Financial ledger engine.
"""

from __future__ import annotations

from typing import Dict, List

from .models import (
    FinancialEvent,
    FinancialEventType,
    LedgerEntry,
    LedgerEntryType,
    SettlementPolicy,
)


class FinancialLedgerEngine:
    """Maintains an idempotent financial ledger."""

    def __init__(self, policy: SettlementPolicy) -> None:
        self.policy = policy

        self.events: List[FinancialEvent] = []
        self.entries: List[LedgerEntry] = []

        self.idempotency_keys: set[str] = set()

    def ingest_event(self, event: FinancialEvent) -> LedgerEntry | None:
        if event.idempotency_key in self.idempotency_keys:
            return None

        entry_type = self._entry_type_for_event(event)

        if entry_type is None:
            return None

        signed_amount = self._signed_amount(event)

        entry = LedgerEntry(
            event_id=event.id,
            idempotency_key=event.idempotency_key,
            entry_type=entry_type,
            marketplace_id=event.marketplace_id,
            tenant_id=event.tenant_id,
            order_id=event.order_id,
            amount=signed_amount,
            currency=event.currency,
        )

        self.events.append(event)
        self.entries.append(entry)
        self.idempotency_keys.add(event.idempotency_key)

        return entry

    def entries_for_period(
        self,
        marketplace_id: str,
        period_start,
        period_end,
        tenant_id: str | None = None,
    ) -> List[LedgerEntry]:
        results: List[LedgerEntry] = []

        for entry in self.entries:
            if entry.marketplace_id != marketplace_id:
                continue

            if tenant_id and entry.tenant_id != tenant_id:
                continue

            if entry.created_at < period_start:
                continue

            if entry.created_at > period_end:
                continue

            results.append(entry)

        return results

    def balance(
        self,
        marketplace_id: str,
        tenant_id: str,
        currency: str,
    ) -> float:
        total = 0.0

        for entry in self.entries:
            if entry.marketplace_id != marketplace_id:
                continue

            if entry.tenant_id != tenant_id:
                continue

            if entry.currency != currency:
                continue

            total += entry.amount

        return round(total, 2)

    def append_entry(self, entry: LedgerEntry) -> LedgerEntry:
        self.entries.append(entry)

        if entry.idempotency_key:
            self.idempotency_keys.add(entry.idempotency_key)

        return entry

    def _entry_type_for_event(
        self,
        event: FinancialEvent,
    ) -> LedgerEntryType | None:
        if event.event_type == FinancialEventType.PAYMENT_CAPTURED:
            return LedgerEntryType.CREDIT

        if event.event_type in {
            FinancialEventType.REFUND_ISSUED,
            FinancialEventType.CHARGEBACK_OPENED,
            FinancialEventType.PAYOUT_COMPLETED,
        }:
            return LedgerEntryType.DEBIT

        if event.event_type == FinancialEventType.FEE_CHARGED:
            return LedgerEntryType.FEE

        if event.event_type == FinancialEventType.TAX_CHARGED:
            return LedgerEntryType.TAX

        if event.event_type == FinancialEventType.ADJUSTMENT:
            return LedgerEntryType.ADJUSTMENT

        return None

    def _signed_amount(self, event: FinancialEvent) -> float:
        if event.event_type == FinancialEventType.PAYMENT_CAPTURED:
            return event.amount

        if event.event_type in {
            FinancialEventType.REFUND_ISSUED,
            FinancialEventType.CHARGEBACK_OPENED,
            FinancialEventType.FEE_CHARGED,
            FinancialEventType.TAX_CHARGED,
            FinancialEventType.PAYOUT_COMPLETED,
        }:
            return -event.amount

        if event.event_type == FinancialEventType.ADJUSTMENT:
            return float(event.payload.get("signed_amount", event.amount))

        return 0.0
