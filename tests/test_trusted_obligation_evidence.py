"""Adversarial tests for trusted runner attestations and the live integrity gate."""
import hashlib
import hmac
import json
from types import SimpleNamespace

from tiannara.application.compilation.integrity_gate import (
    CompilationIntegrityGate,
    GATE_OBLIGATION_EVIDENCE,
)
from tiannara.application.compiler.trusted_obligation_evidence import (
    RetrievedTrustedEvidence,
    TrustedEvidenceAttestation,
    TrustedObligationCertificationRequest,
    TrustedObligationSuitePolicy,
    certify_trusted_obligation_suite,
)
from tiannara.application.evolution.ledger import EvolutionLedger
from tiannara.domain.models.compiler_obligation import (
    Applicability,
    CompilerObligationRecord,
    Disposition,
    EnforcementPoint,
    ScenarioEvidence,
    Strength,
)

SOURCE_HASH = "a" * 64
KEY = b"test-only-trusted-runner-key"
RUNNER = "ci-runner-linux-01"
CONSUMER = "fastapi-runtime@1"
EVIDENCE_REF = "evidence://ci/build-44/workspace-isolation"
PAYLOAD = b"runner=ci-runner-linux-01;scenario=cross-workspace-read-denied;result=PASS"


def signed_attestation(*, signature_override=None, runner_id=RUNNER):
    evidence_hash = hashlib.sha256(PAYLOAD).hexdigest()
    fields = {
        "attestation_id": "attestation-build-44-scenario-1",
        "key_id": "ci-key-1",
        "runner_id": runner_id,
        "source_graph_hash": SOURCE_HASH,
        "obligation_id": "auth.workspace_scope",
        "obligation_hash": obligation_record().obligation_hash,
        "scenario_id": "cross-workspace-read-denied",
        "outcome": "PASS",
        "evidence_ref": EVIDENCE_REF,
        "evidence_sha256": evidence_hash,
        "consumer_binding": CONSUMER,
        "build_id": "build-44",
        "environment_fingerprint": "linux-x86_64-python-3.12-image-sha256-abc",
        "issued_at": "2026-10-13T15:00:00Z",
        "signature_hmac_sha256": "0" * 64,
    }
    canonical = json.dumps(
        {key: value for key, value in fields.items() if key != "signature_hmac_sha256"},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    signature = hmac.new(KEY, canonical, hashlib.sha256).hexdigest()
    fields["signature_hmac_sha256"] = signature_override or signature
    return TrustedEvidenceAttestation(**fields)


def obligation_record(statement="Cross-workspace reads must be denied without disclosing foreign data."):
    scenario = ScenarioEvidence(
        scenario_id="cross-workspace-read-denied",
        outcome="PASS",
        evidence_ref=EVIDENCE_REF,
        evidence_sha256=hashlib.sha256(PAYLOAD).hexdigest(),
        build_id="build-44",
        environment_fingerprint="linux-x86_64-python-3.12-image-sha256-abc",
    )
    return CompilerObligationRecord(
        schema_version="1.0",
        obligation_id="auth.workspace_scope",
        source_graph_id="taskflow-v1",
        source_graph_hash=SOURCE_HASH,
        domain="authorization",
        statement=statement,
        applicability=Applicability.REQUIRED,
        required_strength=Strength.MUST,
        enforcement_points=(
            EnforcementPoint(kind="repository", locator="app/repositories/workspaces.py"),
        ),
        consumer_binding=CONSUMER,
        acceptance_scenarios=(scenario,),
        disposition=Disposition.UNKNOWN,
    )


class FakeTrustedEvidenceStore:
    """Test double for the trusted store boundary; production uses audited storage."""

    def __init__(self, attestation=None):
        self.bundle = RetrievedTrustedEvidence(
            payload=PAYLOAD,
            attestation=attestation or signed_attestation(),
            audit_event_id="evidence-read-audit-1001",
            authorized_principal="compiler-certification-service",
            retrieved_at="2026-10-13T15:01:00Z",
        )
        self.reads = []

    def read(self, evidence_ref):
        self.reads.append(evidence_ref)
        return self.bundle if evidence_ref == EVIDENCE_REF else None


def policy():
    return TrustedObligationSuitePolicy(
        suite_id="taskflow-auth-v1",
        required_obligation_ids=("auth.workspace_scope",),
        expected_consumer_bindings={"auth.workspace_scope": CONSUMER},
        required_scenario_ids={
            "auth.workspace_scope": ("cross-workspace-read-denied",)
        },
    )


def request(*, previously_used=frozenset(), record=None):
    return TrustedObligationCertificationRequest(
        records=(record or obligation_record(),),
        previously_used_attestation_ids=previously_used,
    )


def test_signed_runner_evidence_passes_and_is_bound_to_the_source():
    result = certify_trusted_obligation_suite(
        request(),
        policy=policy(),
        expected_source_graph_hash=SOURCE_HASH,
        evidence_store=FakeTrustedEvidenceStore(),
        trusted_hmac_keys={"ci-key-1": KEY},
        allowed_runner_ids=frozenset({RUNNER}),
    )
    assert result.disposition is Disposition.PASS
    assert result.ok
    assert result.attestation_ids == ("attestation-build-44-scenario-1",)
    assert result.evidence_audit_ids == ("evidence-read-audit-1001",)



def test_signature_cannot_be_reused_after_obligation_semantics_change():
    changed_record = obligation_record(statement="Every workspace read may expose foreign data.")
    result = certify_trusted_obligation_suite(
        request(record=changed_record),
        policy=policy(),
        expected_source_graph_hash=SOURCE_HASH,
        evidence_store=FakeTrustedEvidenceStore(),
        trusted_hmac_keys={"ci-key-1": KEY},
        allowed_runner_ids=frozenset({RUNNER}),
    )
    assert result.disposition is Disposition.UNKNOWN
    assert not result.ok
    assert any("obligation hash binding" in blocker for blocker in result.blockers)

def test_untrusted_runner_cannot_certify():
    result = certify_trusted_obligation_suite(
        request(),
        policy=policy(),
        expected_source_graph_hash=SOURCE_HASH,
        evidence_store=FakeTrustedEvidenceStore(
            signed_attestation(runner_id="untrusted-runner")
        ),
        trusted_hmac_keys={"ci-key-1": KEY},
        allowed_runner_ids=frozenset({RUNNER}),
    )
    assert result.disposition is Disposition.UNKNOWN
    assert not result.ok
    assert any("not allow-listed" in blocker for blocker in result.blockers)


def test_invalid_signature_cannot_certify():
    result = certify_trusted_obligation_suite(
        request(),
        policy=policy(),
        expected_source_graph_hash=SOURCE_HASH,
        evidence_store=FakeTrustedEvidenceStore(
            signed_attestation(signature_override="f" * 64)
        ),
        trusted_hmac_keys={"ci-key-1": KEY},
        allowed_runner_ids=frozenset({RUNNER}),
    )
    assert result.disposition is Disposition.UNKNOWN
    assert any("HMAC signature is invalid" in blocker for blocker in result.blockers)


def test_unknown_key_cannot_certify():
    result = certify_trusted_obligation_suite(
        request(),
        policy=policy(),
        expected_source_graph_hash=SOURCE_HASH,
        evidence_store=FakeTrustedEvidenceStore(),
        trusted_hmac_keys={},
        allowed_runner_ids=frozenset({RUNNER}),
    )
    assert result.disposition is Disposition.UNKNOWN
    assert any("trusted key registry" in blocker for blocker in result.blockers)


def test_replayed_attestation_id_cannot_certify():
    attestation = signed_attestation()
    result = certify_trusted_obligation_suite(
        request(previously_used=frozenset({attestation.attestation_id})),
        policy=policy(),
        expected_source_graph_hash=SOURCE_HASH,
        evidence_store=FakeTrustedEvidenceStore(attestation),
        trusted_hmac_keys={"ci-key-1": KEY},
        allowed_runner_ids=frozenset({RUNNER}),
    )
    assert result.disposition is Disposition.UNKNOWN
    assert any("already consumed" in blocker for blocker in result.blockers)


def test_integrity_gate_records_attestation_and_rejects_replay():
    ledger = EvolutionLedger()
    gate = CompilationIntegrityGate(
        ledger,
        trusted_hmac_keys={"ci-key-1": KEY},
        allowed_runner_ids=frozenset({RUNNER}),
        evidence_store=FakeTrustedEvidenceStore(),
        obligation_policy=policy(),
    )
    compiled = SimpleNamespace(isr_hash=SOURCE_HASH)

    first = gate._gate_i_obligations(compiled, request(), ledger)
    assert first.gate_id == GATE_OBLIGATION_EVIDENCE
    assert first.held
    assert ledger.verify_event_chain()
    recorded = [
        event for event in ledger.events()
        if event.event_type.value == "certification"
    ]
    assert len(recorded) == 1
    assert recorded[0].payload["attestation_ids"] == [
        "attestation-build-44-scenario-1"
    ]
    assert recorded[0].payload["evidence_audit_ids"] == ["evidence-read-audit-1001"]

    second = gate._gate_i_obligations(compiled, request(), ledger)
    assert not second.held
    assert "already consumed" in second.evidence
    assert ledger.verify_event_chain()
    assert len([
        event for event in ledger.events()
        if event.event_type.value == "certification"
    ]) == 2


def test_configured_gate_rejects_missing_obligation_request():
    ledger = EvolutionLedger()
    gate = CompilationIntegrityGate(
        ledger,
        trusted_hmac_keys={"ci-key-1": KEY},
        allowed_runner_ids=frozenset({RUNNER}),
        evidence_store=FakeTrustedEvidenceStore(),
        obligation_policy=policy(),
    )
    result = gate._gate_i_obligations(SimpleNamespace(isr_hash=SOURCE_HASH), None, ledger)
    assert result.gate_id == GATE_OBLIGATION_EVIDENCE
    assert not result.held
    assert "missing or invalid request" in result.evidence


def test_evidence_without_store_audit_receipt_cannot_pass():
    store = FakeTrustedEvidenceStore()
    store.bundle = RetrievedTrustedEvidence(
        payload=PAYLOAD,
        attestation=signed_attestation(),
    )
    result = certify_trusted_obligation_suite(
        request(),
        policy=policy(),
        expected_source_graph_hash=SOURCE_HASH,
        evidence_store=store,
        trusted_hmac_keys={"ci-key-1": KEY},
        allowed_runner_ids=frozenset({RUNNER}),
    )
    assert result.disposition is Disposition.UNKNOWN
    assert not result.ok
    assert any("omitted its access-audit receipt" in blocker for blocker in result.blockers)
