"""Append-only hash-chain support for ESAP transaction evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from .transaction_evidence import TransactionEvidenceRecord


GENESIS_PARENT_DIGEST = None


class TransactionChainError(ValueError):
    """Raised when an evidence chain is invalid or cannot be appended safely."""


@dataclass(frozen=True)
class TransactionEvidenceChain:
    """Immutable ordered transaction-evidence chain."""

    records: tuple[TransactionEvidenceRecord, ...] = ()

    @property
    def tip_digest(self) -> str | None:
        return self.records[-1].digest if self.records else GENESIS_PARENT_DIGEST

    def append(self, record: TransactionEvidenceRecord) -> "TransactionEvidenceChain":
        expected_parent = self.tip_digest
        if record.parent_digest != expected_parent:
            raise TransactionChainError(
                f"parent-digest-mismatch:expected={expected_parent}:actual={record.parent_digest}"
            )
        if not record.verify_digest():
            raise TransactionChainError(f"invalid-record-digest:{record.transaction_id}")
        if any(existing.digest == record.digest for existing in self.records):
            raise TransactionChainError(f"duplicate-record-digest:{record.digest}")
        return TransactionEvidenceChain(records=self.records + (record,))

    def verify(self) -> bool:
        expected_parent = GENESIS_PARENT_DIGEST
        seen: set[str] = set()
        for record in self.records:
            if record.digest in seen:
                return False
            if record.parent_digest != expected_parent:
                return False
            if not record.verify_digest():
                return False
            seen.add(record.digest)
            expected_parent = record.digest
        return True


def build_chain(records: Iterable[TransactionEvidenceRecord]) -> TransactionEvidenceChain:
    """Build and validate a chain in the supplied order."""
    chain = TransactionEvidenceChain()
    for record in records:
        chain = chain.append(record)
    return chain


def verify_transaction_evidence_chain(
    records: Sequence[TransactionEvidenceRecord],
) -> bool:
    """Verify ordering, linkage, and content-addressed integrity."""
    return build_chain(records).verify()
