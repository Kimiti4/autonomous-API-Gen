"""Tests for cryptographic signing of AuditEvidenceISR (Phase 28 Milestone 5)."""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from constitutional_architecture.governance.audit import AuditEvidenceRecorder
from constitutional_architecture.governance.evidence_signing import (
    HmacEvidenceSigner,
    SignedAuditEvidenceRecorder,
    sign_evidence,
    verify_evidence_signature,
    new_evidence_recorder,
)
from constitutional_architecture.governance.exceptions import ExceptionRegistry
from constitutional_architecture.governance.governance_dashboard import GovernanceDashboard
from constitutional_architecture.governance.integration import GovernedKernel
from constitutional_architecture.governance.schemas import AuditEvidenceISR
from constitutional_architecture.governance.versioning import (
    InMemoryConstitutionVersionRepository,
    VersionManager,
)

NOW = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def _base_evidence() -> AuditEvidenceISR:
    rec = AuditEvidenceRecorder()
    return rec.record(
        actor="architect",
        event_kind="decision",
        subject_ref="subject:1",
        payload={"outcome": "ALLOW"},
        recorded_at=NOW,
    )


def test_hmac_roundtrip_valid():
    signer = HmacEvidenceSigner(b"secret-key")
    ev = _base_evidence()
    signed = sign_evidence(ev, signer, "signer-1")
    assert signed.signature is not None
    assert signed.signer_id == "signer-1"
    assert verify_evidence_signature(signed, signer) is True


def test_unsigned_evidence_passes_backward_compatible():
    signer = HmacEvidenceSigner(b"secret-key")
    ev = _base_evidence()
    assert ev.signature is None
    assert verify_evidence_signature(ev, signer) is True


def test_tampered_payload_hash_detected():
    signer = HmacEvidenceSigner(b"secret-key")
    signed = sign_evidence(_base_evidence(), signer, "signer-1")
    tampered = signed.model_copy(update={"payload_hash": "tampered"})
    assert verify_evidence_signature(tampered, signer) is False


def test_tampered_chain_link_detected_independently_of_hash_chain():
    signer = HmacEvidenceSigner(b"secret-key")
    rec = AuditEvidenceRecorder()
    first = rec.record(actor="a", event_kind="k", subject_ref="s", payload={}, recorded_at=NOW)
    second = rec.record(actor="a", event_kind="k", subject_ref="s", payload={}, recorded_at=NOW)
    signed_first = sign_evidence(first, signer, "signer-1")
    # Forge a record whose link points elsewhere, then sign it: its signature is
    # valid for the forged link, but the signed first record's link is now stale.
    forged = second.model_copy(update={"chain_link": "ev-bogus"})
    forged_signed = sign_evidence(forged, signer, "signer-1")
    assert verify_evidence_signature(forged_signed, signer) is True
    broken = signed_first.model_copy(update={"chain_link": "ev-bogus"})
    assert verify_evidence_signature(broken, signer) is False


def test_wrong_key_does_not_verify():
    signer = HmacEvidenceSigner(b"correct-key")
    other = HmacEvidenceSigner(b"wrong-key")
    signed = sign_evidence(_base_evidence(), signer, "signer-1")
    assert verify_evidence_signature(signed, other) is False


def test_signed_recorder_emits_signed_records_and_chain_holds():
    signer = HmacEvidenceSigner(b"secret-key")
    recorder = SignedAuditEvidenceRecorder(signer, "signer-1")
    a = recorder.record(
        actor="architect", event_kind="decision",
        subject_ref="s", payload={"o": "ALLOW"}, recorded_at=NOW,
    )
    b = recorder.record(
        actor="architect", event_kind="decision",
        subject_ref="s", payload={"o": "DENY"}, recorded_at=NOW,
    )
    assert a.signature is not None and b.signature is not None
    assert a.signer_id == "signer-1" and b.signer_id == "signer-1"
    assert a.chain_link is None
    assert b.chain_link == a.evidence_id
    assert recorder.verify_chain() is True
    assert recorder.verify_signatures() is True


def test_signed_recorder_detects_tampered_signature():
    signer = HmacEvidenceSigner(b"secret-key")
    other = HmacEvidenceSigner(b"other-key")
    recorder = SignedAuditEvidenceRecorder(signer, "signer-1")
    recorder.record(actor="a", event_kind="k", subject_ref="s", payload={}, recorded_at=NOW)
    ev = _base_evidence()
    forged = sign_evidence(ev, other, "attacker")
    assert verify_evidence_signature(forged, signer) is False


def test_recorder_uses_its_own_signer_key():
    signer = HmacEvidenceSigner(b"secret-key")
    other = HmacEvidenceSigner(b"other-key")
    recorder = SignedAuditEvidenceRecorder(signer, "signer-1")
    recorder.record(actor="a", event_kind="k", subject_ref="s", payload={}, recorded_at=NOW)
    for entry in recorder.entries:
        assert verify_evidence_signature(entry, signer) is True
        assert verify_evidence_signature(entry, other) is False


@pytest.mark.parametrize("factory", [HmacEvidenceSigner])
def test_signer_requires_a_key(factory):
    with pytest.raises(TypeError):
        factory()  # no key -> constructor must reject


def test_factory_returns_signing_ledger_when_key_configured():
    recorder = new_evidence_recorder(key="env-like-secret")
    assert isinstance(recorder, SignedAuditEvidenceRecorder)
    signed = recorder.record(
        actor="architect", event_kind="decision",
        subject_ref="s", payload={"o": "ALLOW"}, recorded_at=NOW,
    )
    assert signed.signature is not None
    assert recorder.verify_chain() is True
    assert recorder.verify_signatures() is True


def test_factory_returns_unsigned_ledger_and_warns_when_key_absent(monkeypatch):
    monkeypatch.delenv("AUDIT_EVIDENCE_SIGNING_KEY", raising=False)
    with pytest.warns(UserWarning, match="AUDIT_EVIDENCE_SIGNING_KEY is not set"):
        recorder = new_evidence_recorder()
    assert isinstance(recorder, AuditEvidenceRecorder)
    assert not isinstance(recorder, SignedAuditEvidenceRecorder)
    unsigned = recorder.record(
        actor="architect", event_kind="decision",
        subject_ref="s", payload={"o": "ALLOW"}, recorded_at=NOW,
    )
    assert unsigned.signature is None
    assert recorder.verify_signatures() is None  # N/A for unsigned ledger


def _stub_kernel():
    class Stub:
        def __init__(self):
            self.requests = []

        def evaluate(self, request):
            self.requests.append(request)
            return {"decision": "permit"}

    return Stub()


def test_governed_kernel_emits_signed_records_when_keyed(monkeypatch):
    monkeypatch.delenv("AUDIT_EVIDENCE_SIGNING_KEY", raising=False)
    governed = GovernedKernel(_stub_kernel(), evidence=new_evidence_recorder(key="kernel-key"))
    governed.evaluate(SimpleNamespace(request_id="rq-1"))
    assert len(governed._evidence.entries) == 1
    entry = governed._evidence.entries[0]
    assert entry.signature is not None
    assert governed._evidence.verify_chain() is True
    assert governed._evidence.verify_signatures() is True


def test_governed_kernel_records_unsigned_when_key_absent(monkeypatch):
    monkeypatch.delenv("AUDIT_EVIDENCE_SIGNING_KEY", raising=False)
    with pytest.warns(UserWarning):
        governed = GovernedKernel(_stub_kernel(), evidence=new_evidence_recorder())
    governed.evaluate(SimpleNamespace(request_id="rq-2"))
    assert governed._evidence.entries[0].signature is None


def _dashboard(recorder):
    versions = VersionManager(InMemoryConstitutionVersionRepository())
    return GovernanceDashboard(versions, recorder, ExceptionRegistry(), type(
        "_R", (), {"latest": lambda self, n=20: ()})())


def test_dashboard_projects_signature_status_signed():
    signer = HmacEvidenceSigner(b"secret-key")
    recorder = SignedAuditEvidenceRecorder(signer, "signer-1")
    recorder.record(
        actor="architect", event_kind="decision",
        subject_ref="s", payload={"o": "ALLOW"}, recorded_at=NOW,
    )
    view = _dashboard(recorder).project(now=NOW)
    assert view.evidence_signed is True
    assert view.evidence_signatures_valid is True
    assert view.evidence_chain_intact is True


def test_dashboard_projects_signature_status_unsigned():
    import warnings as _w

    with _w.catch_warnings():
        _w.simplefilter("ignore")
        recorder = AuditEvidenceRecorder()
    recorder.record(
        actor="architect", event_kind="decision",
        subject_ref="s", payload={"o": "ALLOW"}, recorded_at=NOW,
    )
    view = _dashboard(recorder).project(now=NOW)
    assert view.evidence_signed is False
    assert view.evidence_signatures_valid is None
    assert view.evidence_chain_intact is True
