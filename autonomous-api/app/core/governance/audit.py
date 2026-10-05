"""Tamper-evident governance audit records.

The audit envelope is separate from domain events: it binds candidate scope,
event ordering, predecessor hash, canonical event payload, and an HMAC
signature. Verification is fail-closed.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass


class AuditIntegrityError(RuntimeError):
    """Raised when a persisted governance audit chain cannot be verified."""


def _canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@dataclass(frozen=True)
class AuditRecord:
    candidate_id: str
    sequence: int
    event_type: str
    payload: str
    previous_hash: str
    record_hash: str
    signature: str


class GovernanceAuditSigner:
    """HMAC-SHA256 signer for the durable governance audit envelope."""

    algorithm = "hmac-sha256"

    def __init__(self, key: str):
        if not key:
            raise ValueError("governance audit signing key must be configured")
        self._key = key.encode("utf-8")

    def sign(self, *, candidate_id: str, sequence: int, event_type: str,
             payload: str, previous_hash: str) -> tuple[str, str]:
        material = _canonical({
            "candidate_id": candidate_id,
            "sequence": sequence,
            "event_type": event_type,
            "payload": payload,
            "previous_hash": previous_hash,
        }).encode("utf-8")
        record_hash = hashlib.sha256(material).hexdigest()
        signature = hmac.new(
            self._key, record_hash.encode("ascii"), hashlib.sha256
        ).hexdigest()
        return record_hash, signature

    def verify(self, record: AuditRecord) -> None:
        expected_hash, expected_signature = self.sign(
            candidate_id=record.candidate_id,
            sequence=record.sequence,
            event_type=record.event_type,
            payload=record.payload,
            previous_hash=record.previous_hash,
        )
        if not hmac.compare_digest(record.record_hash, expected_hash):
            raise AuditIntegrityError(
                f"governance audit hash mismatch at {record.candidate_id}:{record.sequence}"
            )
        if not hmac.compare_digest(record.signature, expected_signature):
            raise AuditIntegrityError(
                f"governance audit signature mismatch at {record.candidate_id}:{record.sequence}"
            )


def verify_chain(records: list[AuditRecord], signer: GovernanceAuditSigner) -> None:
    expected_previous = ""
    expected_sequence = 1
    for record in records:
        if record.sequence != expected_sequence:
            raise AuditIntegrityError(
                f"governance audit sequence gap at {record.candidate_id}:{record.sequence}"
            )
        if record.previous_hash != expected_previous:
            raise AuditIntegrityError(
                f"governance audit predecessor mismatch at "
                f"{record.candidate_id}:{record.sequence}"
            )
        signer.verify(record)
        expected_previous = record.record_hash
        expected_sequence += 1
