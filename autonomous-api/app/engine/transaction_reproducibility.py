"""Deterministic reproducibility primitives for ESAP transactions."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Sequence

from .transaction_evidence import TransactionEvidenceRecord, _digest


@dataclass(frozen=True)
class ReproducibilityFingerprint:
    """Stable identity for the complete canonical transaction evidence."""

    schema_version: str
    transaction_id: str
    digest: str

    def as_key(self) -> str:
        return f"{self.schema_version}:{self.transaction_id}:{self.digest}"


def fingerprint_transaction(
    record: TransactionEvidenceRecord,
) -> ReproducibilityFingerprint:
    """Derive a stable fingerprint after validating content integrity."""
    if not record.verify_digest():
        raise ValueError(f"invalid-record-digest:{record.transaction_id}")
    return ReproducibilityFingerprint(
        schema_version=record.schema_version,
        transaction_id=record.transaction_id,
        digest=record.digest,
    )


def canonical_bytes(record: TransactionEvidenceRecord) -> bytes:
    """Return the exact deterministic byte representation hashed by the record."""
    if not record.verify_digest():
        raise ValueError(f"invalid-record-digest:{record.transaction_id}")
    return record.to_json().encode("utf-8")


def replay_equivalent(
    expected: TransactionEvidenceRecord,
    replay: TransactionEvidenceRecord,
) -> bool:
    """Require byte-for-byte canonical evidence equality for deterministic replay."""
    return canonical_bytes(expected) == canonical_bytes(replay)


def chain_reproducibility_digest(records: Sequence[TransactionEvidenceRecord]) -> str:
    """Derive a deterministic digest for an ordered evidence sequence."""
    if not records:
        return hashlib.sha256(b"esap.transaction-chain.genesis").hexdigest()
    payload = b"".join(canonical_bytes(record) for record in records)
    return hashlib.sha256(payload).hexdigest()
