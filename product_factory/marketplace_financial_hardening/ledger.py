"""
Financial ledger engine.

Append-only, idempotency-guaranteed ledger for marketplace financial events.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .models import (
    FinancialAuditEvent,
    FinancialLedgerEntry,
    LedgerEntryType,
)


class FinancialLedgerEngine:
    """Normalized financial ledger with idempotent, append-only writes."""

    def __init__(self) -> None:
        self.entries: Dict[str, FinancialLedgerEntry] = {}
        self._idempotency_keys: set = set()
        self.audit_events: List[FinancialAuditEvent] = []

    def append(self, entry: FinancialLedgerEntry) -> bool:
        """Append a ledger entry. Returns False if the idempotency key is a duplicate."""
        if entry.idempotency_key and entry.idempotency_key in self._idempotency_keys:
            return False

        if entry.idempotency_key:
            self._idempotency_keys.add(entry.idempotency_key)

        self.entries[entry.ledger_id] = entry

        self.audit_events.append(
            FinancialAuditEvent(
                marketplace_id=entry.marketplace_id,
                action="ledger_entry_appended",
                actor="financial_ledger",
                status="OK",
                amount=entry.amount,
                currency=entry.currency,
                idempotency_key=entry.idempotency_key,
                source_event_id=entry.source_event_id,
                evidence_ref=entry.evidence_ref,
                reason=entry.entry_type.value,
            )
        )

        return True

    def get(self, ledger_id: str) -> Optional[FinancialLedgerEntry]:
        return self.entries.get(ledger_id)

    def by_order(
        self,
        order_id: str,
        marketplace_id: Optional[str] = None,
    ) -> List[FinancialLedgerEntry]:
        result = [e for e in self.entries.values() if e.order_id == order_id]

        if marketplace_id:
            result = [e for e in result if e.marketplace_id == marketplace_id]

        return result

    def by_entry_type(
        self,
        entry_type: LedgerEntryType,
        marketplace_id: Optional[str] = None,
    ) -> List[FinancialLedgerEntry]:
        result = [
            e for e in self.entries.values() if e.entry_type == entry_type
        ]

        if marketplace_id:
            result = [e for e in result if e.marketplace_id == marketplace_id]

        return result

    def by_source_event(
        self,
        source_event_id: str,
        marketplace_id: Optional[str] = None,
    ) -> List[FinancialLedgerEntry]:
        result = [
            e
            for e in self.entries.values()
            if e.source_event_id == source_event_id
        ]

        if marketplace_id:
            result = [e for e in result if e.marketplace_id == marketplace_id]

        return result

    def record_audit(self, event: FinancialAuditEvent) -> FinancialAuditEvent:
        self.audit_events.append(event)

        return event

    def duplicate_idempotency_keys(self) -> List[str]:
        seen: Dict[str, int] = {}

        for entry in self.entries.values():
            if not entry.idempotency_key:
                continue

            seen[entry.idempotency_key] = seen.get(entry.idempotency_key, 0) + 1

        return [key for key, count in seen.items() if count > 1]

    def total_count(self) -> int:
        return len(self.entries)

    def report(
        self,
        marketplace_id: Optional[str] = None,
    ) -> List[FinancialLedgerEntry]:
        if not marketplace_id:
            return list(self.entries.values())

        return [e for e in self.entries.values() if e.marketplace_id == marketplace_id]
