"""Phase-28 governance audit integrity tests."""
from __future__ import annotations

import pytest

from app.core.governance.audit import (
    AuditIntegrityError,
    AuditRecord,
    GovernanceAuditSigner,
    verify_chain,
)


def _record(signer, sequence, previous_hash, payload="{}"):
    record_hash, signature = signer.sign(
        candidate_id="c1",
        sequence=sequence,
        event_type="GovernanceDecisionMade",
        payload=payload,
        previous_hash=previous_hash,
    )
    return AuditRecord(
        candidate_id="c1",
        sequence=sequence,
        event_type="GovernanceDecisionMade",
        payload=payload,
        previous_hash=previous_hash,
        record_hash=record_hash,
        signature=signature,
    )


def test_audit_chain_is_hash_linked_and_signed():
    signer = GovernanceAuditSigner("test-key")
    first = _record(signer, 1, "")
    second = _record(signer, 2, first.record_hash)

    verify_chain([first, second], signer)


def test_audit_chain_rejects_payload_tampering():
    signer = GovernanceAuditSigner("test-key")
    first = _record(signer, 1, "")
    tampered = AuditRecord(
        candidate_id=first.candidate_id,
        sequence=first.sequence,
        event_type=first.event_type,
        payload='{"tampered":true}',
        previous_hash=first.previous_hash,
        record_hash=first.record_hash,
        signature=first.signature,
    )

    with pytest.raises(AuditIntegrityError, match="hash mismatch"):
        verify_chain([tampered], signer)


def test_audit_chain_rejects_reordering_or_gaps():
    signer = GovernanceAuditSigner("test-key")
    first = _record(signer, 1, "")
    third = _record(signer, 3, first.record_hash)

    with pytest.raises(AuditIntegrityError, match="sequence gap"):
        verify_chain([first, third], signer)


def test_audit_chain_rejects_signature_tampering():
    signer = GovernanceAuditSigner("test-key")
    first = _record(signer, 1, "")
    tampered = AuditRecord(
        candidate_id=first.candidate_id,
        sequence=first.sequence,
        event_type=first.event_type,
        payload=first.payload,
        previous_hash=first.previous_hash,
        record_hash=first.record_hash,
        signature="0" * len(first.signature),
    )

    with pytest.raises(AuditIntegrityError, match="signature mismatch"):
        verify_chain([tampered], signer)


def test_signer_requires_key():
    with pytest.raises(ValueError, match="signing key"):
        GovernanceAuditSigner("")
