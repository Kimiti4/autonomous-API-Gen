import hashlib
import json

import pytest

from tiannara.application.compiler.filesystem_evidence_store import (
    EvidenceReadAuditReceipt,
    FileSystemTrustedEvidenceStore,
)

PAYLOAD = b"scenario result"
EVIDENCE_REF = "evidence://ci/build-44/workspace-isolation"


def _attestation(payload=PAYLOAD):
    return {
        "attestation_id": "attestation-build-44-scenario-1",
        "key_id": "ci-key-1",
        "runner_id": "ci-runner-linux-01",
        "source_graph_hash": "a" * 64,
        "obligation_id": "auth.workspace_scope",
        "obligation_hash": "b" * 64,
        "scenario_id": "cross-workspace-read-denied",
        "outcome": "PASS",
        "evidence_ref": EVIDENCE_REF,
        "evidence_sha256": hashlib.sha256(payload).hexdigest(),
        "consumer_binding": "fastapi-runtime@1",
        "build_id": "build-44",
        "environment_fingerprint": "linux-x86_64-image-sha256-abc",
        "issued_at": "2026-10-14T00:00:00Z",
        "signature_hmac_sha256": "c" * 64,
    }


def _receipt():
    return EvidenceReadAuditReceipt(
        audit_event_id="audit-event-0001",
        authorized_principal="compiler-certification-service",
        retrieved_at="2026-10-14T00:01:00Z",
    )


def _write_evidence(root):
    base = root / "ci" / "build-44" / "workspace-isolation"
    base.parent.mkdir(parents=True)
    base.with_suffix(".bin").write_bytes(PAYLOAD)
    base.with_suffix(".attestation.json").write_text(
        json.dumps(_attestation()), encoding="utf-8"
    )


def test_read_returns_store_audit_receipt_with_payload_and_attestation(tmp_path):
    _write_evidence(tmp_path)
    calls = []

    def audit_read(reference, outcome, payload_hash, attestation_id):
        calls.append((reference, outcome, payload_hash, attestation_id))
        return _receipt()

    store = FileSystemTrustedEvidenceStore(tmp_path, audit_read=audit_read)
    result = store.read(EVIDENCE_REF)

    assert result is not None
    assert result.payload == PAYLOAD
    assert result.attestation.attestation_id == _attestation()["attestation_id"]
    assert result.audit_event_id == "audit-event-0001"
    assert result.authorized_principal == "compiler-certification-service"
    assert result.retrieved_at == "2026-10-14T00:01:00Z"
    assert calls == [(
        EVIDENCE_REF,
        "READ",
        hashlib.sha256(PAYLOAD).hexdigest(),
        _attestation()["attestation_id"],
    )]


def test_missing_evidence_is_audited_and_returns_none(tmp_path):
    calls = []

    def audit_read(reference, outcome, payload_hash, attestation_id):
        calls.append((reference, outcome, payload_hash, attestation_id))
        return _receipt()

    store = FileSystemTrustedEvidenceStore(tmp_path, audit_read=audit_read)
    assert store.read(EVIDENCE_REF) is None
    assert calls == [(EVIDENCE_REF, "NOT_FOUND", "", "")]


def test_invalid_reference_is_audited_before_error_is_raised(tmp_path):
    calls = []

    def audit_read(reference, outcome, payload_hash, attestation_id):
        calls.append((reference, outcome, payload_hash, attestation_id))
        return _receipt()

    store = FileSystemTrustedEvidenceStore(tmp_path, audit_read=audit_read)
    with pytest.raises(ValueError, match="invalid path"):
        store.read("evidence://ci/../outside")
    assert calls == [("evidence://ci/../outside", "INVALID_REFERENCE", "", "")]


def test_read_fails_closed_when_audit_callback_returns_no_receipt(tmp_path):
    _write_evidence(tmp_path)
    store = FileSystemTrustedEvidenceStore(
        tmp_path,
        audit_read=lambda *_args: None,
    )
    with pytest.raises(ValueError, match="EvidenceReadAuditReceipt"):
        store.read(EVIDENCE_REF)


def test_read_fails_closed_when_audit_callback_raises(tmp_path):
    _write_evidence(tmp_path)

    def broken_audit(*_args):
        raise RuntimeError("audit persistence unavailable")

    store = FileSystemTrustedEvidenceStore(tmp_path, audit_read=broken_audit)
    with pytest.raises(RuntimeError, match="audit persistence unavailable"):
        store.read(EVIDENCE_REF)


@pytest.mark.parametrize(
    "field",
    ["audit_event_id", "authorized_principal", "retrieved_at"],
)
def test_audit_receipt_rejects_missing_required_metadata(field):
    values = {
        "audit_event_id": "audit-event-0001",
        "authorized_principal": "compiler-certification-service",
        "retrieved_at": "2026-10-14T00:01:00Z",
    }
    values[field] = " "
    with pytest.raises(ValueError, match=field):
        EvidenceReadAuditReceipt(**values)
