"""Append-only in-memory ledger for deterministic ESAP transaction evidence."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .transaction_evidence import TransactionEvidenceRecord


@dataclass(frozen=True)
class EvidenceLedger:
    """Immutable ledger snapshot.

    Records are accepted only when their digest is valid and their parent
    digest exactly matches the current tail. The first record must have no
    parent. Duplicate transaction IDs are rejected.
    """

    records: tuple[TransactionEvidenceRecord, ...] = ()

    @property
    def head(self) -> TransactionEvidenceRecord | None:
        return self.records[-1] if self.records else None

    @property
    def head_digest(self) -> str | None:
        return self.head.digest if self.head else None

    def append(self, record: TransactionEvidenceRecord) -> "EvidenceLedger":
        if not record.verify_digest():
            raise ValueError("ledger-invalid-record-digest")
        if any(existing.transaction_id == record.transaction_id for existing in self.records):
            raise ValueError("ledger-duplicate-transaction:" + record.transaction_id)

        expected_parent = self.head_digest
        if self.head is not None and not bool(self.head.admission.get("admitted", False)):
            raise ValueError("ledger-cannot-extend-rejected-head")
        if record.parent_digest != expected_parent:
            if expected_parent is None and record.parent_digest is not None:
                raise ValueError("ledger-unexpected-parent-digest")
            raise ValueError("ledger-parent-digest-mismatch")

        return EvidenceLedger(self.records + (record,))

    def verify(self) -> bool:
        previous: str | None = None
        seen: set[str] = set()
        for record in self.records:
            if record.transaction_id in seen or not record.verify_digest():
                return False
            if record.parent_digest != previous:
                return False
            seen.add(record.transaction_id)
            previous = record.digest
        return True

    def transaction(self, transaction_id: str) -> TransactionEvidenceRecord | None:
        return next((r for r in self.records if r.transaction_id == transaction_id), None)


def replay_ledger(records: Iterable[TransactionEvidenceRecord]) -> EvidenceLedger:
    ledger = EvidenceLedger()
    for record in records:
        ledger = ledger.append(record)
    return ledger
