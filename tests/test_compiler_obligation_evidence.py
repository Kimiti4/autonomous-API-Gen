"""Adversarial tests for independent obligation evidence verification."""
import hashlib

from tiannara.application.compiler.obligation_evidence import verify_obligation_evidence
from tiannara.domain.models.compiler_obligation import (
    Applicability,
    CompilerObligationRecord,
    Disposition,
    EnforcementPoint,
    ScenarioEvidence,
    Strength,
)

SOURCE_HASH = "a" * 64
PAYLOAD = b"trusted test-runner evidence: scenario cross-workspace-read-denied passed"


def passing_record(**overrides):
    scenario = ScenarioEvidence(
        scenario_id="cross-workspace-read-denied",
        outcome="PASS",
        evidence_ref="evidence://runs/build-1/scenario-1",
        evidence_sha256=hashlib.sha256(PAYLOAD).hexdigest(),
        build_id="build-1",
        environment_fingerprint="python-3.12-linux-x86_64",
    )
    data = {
        "schema_version": "1.0",
        "obligation_id": "auth.workspace_scope",
        "source_graph_id": "taskflow-v1",
        "source_graph_hash": SOURCE_HASH,
        "domain": "authorization",
        "statement": "Every workspace read is scoped to the authenticated member.",
        "applicability": Applicability.REQUIRED,
        "required_strength": Strength.MUST,
        "consumer_binding": "fastapi-runtime@1",
        "enforcement_points": (
            EnforcementPoint(kind="repository", locator="app/repositories/workspaces.py"),
        ),
        "acceptance_scenarios": (scenario,),
        "disposition": Disposition.UNKNOWN,
    }
    data.update(overrides)
    return CompilerObligationRecord(**data)


def verify(record, evidence=PAYLOAD, **kwargs):
    return verify_obligation_evidence(
        record,
        expected_source_graph_hash=kwargs.pop("expected_source_graph_hash", SOURCE_HASH),
        required_scenario_ids=kwargs.pop("required_scenario_ids", ("cross-workspace-read-denied",)),
        evidence_bytes_by_ref=kwargs.pop(
            "evidence_bytes_by_ref",
            {"evidence://runs/build-1/scenario-1": evidence},
        ),
        expected_consumer_binding=kwargs.pop("expected_consumer_binding", "fastapi-runtime@1"),
    )


def test_independent_verifier_promotes_unknown_only_with_matching_evidence():
    verdict = verify(passing_record())
    assert verdict.disposition is Disposition.PASS
    assert verdict.ok
    assert verdict.verified_scenarios == ("cross-workspace-read-denied",)


def test_missing_evidence_cannot_pass():
    verdict = verify(passing_record(), evidence_bytes_by_ref={})
    assert verdict.disposition is Disposition.UNKNOWN
    assert not verdict.ok
    assert verdict.invalid_evidence_refs


def test_tampered_evidence_cannot_pass():
    verdict = verify(passing_record(), evidence=b"tampered")
    assert verdict.disposition is Disposition.UNKNOWN
    assert any("hash mismatch" in blocker for blocker in verdict.blockers)


def test_stale_source_hash_cannot_pass():
    verdict = verify(passing_record(), expected_source_graph_hash="c" * 64)
    assert verdict.disposition is Disposition.UNKNOWN
    assert any("source graph hash" in blocker for blocker in verdict.blockers)


def test_wrong_consumer_cannot_pass():
    verdict = verify(passing_record(), expected_consumer_binding="other-runtime@1")
    assert verdict.disposition is Disposition.UNKNOWN
    assert any("consumer binding" in blocker for blocker in verdict.blockers)


def test_missing_required_scenario_cannot_pass():
    verdict = verify(passing_record(), required_scenario_ids=("cross-workspace-read-denied", "delete-foreign-workspace"))
    assert verdict.disposition is Disposition.UNKNOWN
    assert verdict.missing_scenarios == ("delete-foreign-workspace",)


def test_empty_acceptance_suite_cannot_pass():
    verdict = verify(passing_record(), required_scenario_ids=())
    assert verdict.disposition is Disposition.UNKNOWN
    assert any("at least one required" in blocker for blocker in verdict.blockers)


def test_recorded_failure_remains_failure_even_if_evidence_bytes_match():
    record = passing_record(disposition=Disposition.FAIL)
    verdict = verify(record)
    assert verdict.disposition is Disposition.FAIL
    assert not verdict.ok


def test_string_payload_is_not_accepted_as_evidence_bytes():
    verdict = verify(passing_record(), evidence="not bytes")
    assert verdict.disposition is Disposition.UNKNOWN
    assert any("not bytes" in blocker for blocker in verdict.blockers)


def test_observed_scenario_failure_is_fail_not_unknown():
    original = passing_record().acceptance_scenarios[0]
    failed_scenario = original.model_copy(update={"outcome": "FAIL"})
    record = passing_record(acceptance_scenarios=(failed_scenario,))
    verdict = verify(record)
    assert verdict.disposition is Disposition.FAIL
    assert not verdict.ok
