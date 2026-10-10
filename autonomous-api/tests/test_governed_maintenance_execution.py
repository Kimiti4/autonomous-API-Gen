import pytest

from app.engine.deployed_app_observation import (
    ObservationStatus,
    RuntimeObservation,
    assess_deployed_observation,
)
from app.engine.governed_maintenance_execution import record_verified_maintenance
from app.engine.repair_report import build_repair_report


def setup_case(**admission_overrides):
    observation = RuntimeObservation(
        deployment_id="staging-1",
        observed_revision="rev-a",
        environment_fingerprint="env-a",
        status=ObservationStatus.HEALTHY,
        health_evidence=("health:pass",),
        verification_evidence=("smoke:pass",),
    )
    values = dict(
        baseline_revision="rev-a",
        baseline_environment_fingerprint="env-a",
        authorized_obligation_ids=("ob-17",),
        explicit_change_authorization=True,
    )
    values.update(admission_overrides)
    admission = assess_deployed_observation(observation, **values)
    report = build_repair_report(
        report_id="repair-17",
        target="staging-1",
        source_revision="rev-a",
        finding_ids=("finding-1",),
        root_causes=(),
        candidates_considered=(),
        selected_candidate_id="repair-candidate-1",
        patch_digest="sha256:patch-123",
        verification=({"passed": True, "evidence_refs": ("ci:run-17", "regression:run-17")},),
        regressions=({"detected": False, "evidence_ref": "regression:run-17"},),
        measurements=(),
        residuals=(),
        deployment_ready=False,
    )
    return observation, admission, report


def test_records_verified_repair_and_emits_digest_linked_event():
    observation, admission, report = setup_case()
    record, event = record_verified_maintenance(
        observation,
        admission,
        obligation_id="ob-17",
        authorization_ref="approval:ticket-17",
        repair_report=report,
    )
    assert record.patch_digest == report.patch_digest
    assert record.observation_digest == observation.digest
    assert record.verification_evidence == (
        "verification:0:ci:run-17",
        "verification:0:regression:run-17",
    )
    assert event.status == "verified"
    assert event.repair_report_digest == report.digest
    assert len(event.digest) == 64


def test_rejects_report_with_failed_verification():
    observation, admission, report = setup_case()
    failed = build_repair_report(
        report_id="repair-failed",
        target="staging-1",
        source_revision="rev-a",
        finding_ids=("finding-1",),
        root_causes=(),
        candidates_considered=(),
        selected_candidate_id="repair-candidate-1",
        patch_digest="sha256:patch-123",
        verification=({"passed": False, "evidence_refs": ("ci:failed",)},),
        regressions=(),
        measurements=(),
        residuals=("verification-failed",),
        deployment_ready=False,
    )
    with pytest.raises(ValueError, match="repair-report-verification-failed"):
        record_verified_maintenance(
            observation, admission, obligation_id="ob-17",
            authorization_ref="approval:ticket-17", repair_report=failed,
        )


def test_rejects_report_with_missing_verification_evidence():
    observation, admission, report = setup_case()
    no_evidence = build_repair_report(
        report_id="repair-no-evidence",
        target="staging-1",
        source_revision="rev-a",
        finding_ids=("finding-1",),
        root_causes=(),
        candidates_considered=(),
        selected_candidate_id="repair-candidate-1",
        patch_digest="sha256:patch-123",
        verification=({"passed": True},),
        regressions=({"detected": False, "evidence_ref": "regression:run-17"},),
        measurements=(),
        residuals=(),
        deployment_ready=False,
    )
    with pytest.raises(ValueError, match="repair-report-verification-evidence-missing"):
        record_verified_maintenance(
            observation, admission, obligation_id="ob-17",
            authorization_ref="approval:ticket-17", repair_report=no_evidence,
        )


def test_staging_record_does_not_authorize_production_write():
    observation, admission, report = setup_case()
    with pytest.raises(ValueError, match="production-write-not-authorized"):
        record_verified_maintenance(
            observation, admission, obligation_id="ob-17",
            authorization_ref="approval:ticket-17", repair_report=report,
            production_write_requested=True,
        )


def test_rejects_report_for_stale_source_revision():
    observation, admission, report = setup_case()
    stale = build_repair_report(
        report_id="repair-stale",
        target="staging-1",
        source_revision="rev-old",
        finding_ids=("finding-1",),
        root_causes=(),
        candidates_considered=(),
        selected_candidate_id="repair-candidate-1",
        patch_digest="sha256:patch-123",
        verification=({"passed": True, "evidence_refs": ("ci:run-17",)},),
        regressions=(),
        measurements=(),
        residuals=(),
        deployment_ready=False,
    )
    with pytest.raises(ValueError, match="repair-report-source-revision-mismatch"):
        record_verified_maintenance(
            observation, admission, obligation_id="ob-17",
            authorization_ref="approval:ticket-17", repair_report=stale,
        )



def test_rejects_missing_regression_evidence():
    observation, admission, report = setup_case()
    missing = build_repair_report(
        report_id="repair-no-regression-evidence",
        target="staging-1",
        source_revision="rev-a",
        finding_ids=("finding-1",),
        root_causes=(),
        candidates_considered=(),
        selected_candidate_id="repair-candidate-1",
        patch_digest="sha256:patch-123",
        verification=({"passed": True, "evidence_refs": ("ci:run-17",)},),
        regressions=(),
        measurements=(),
        residuals=(),
        deployment_ready=False,
    )
    with pytest.raises(ValueError, match="repair-report-regression-evidence-missing"):
        record_verified_maintenance(
            observation, admission, obligation_id="ob-17",
            authorization_ref="approval:ticket-17", repair_report=missing,
        )


def test_rejects_detected_regression_even_when_verification_passed():
    observation, admission, report = setup_case()
    regressed = build_repair_report(
        report_id="repair-regressed",
        target="staging-1",
        source_revision="rev-a",
        finding_ids=("finding-1",),
        root_causes=(),
        candidates_considered=(),
        selected_candidate_id="repair-candidate-1",
        patch_digest="sha256:patch-123",
        verification=({"passed": True, "evidence_refs": ("ci:run-17",)},),
        regressions=({"detected": True, "evidence_ref": "regression:failed"},),
        measurements=(),
        residuals=(),
        deployment_ready=False,
    )
    with pytest.raises(ValueError, match="repair-report-regression-detected"):
        record_verified_maintenance(
            observation, admission, obligation_id="ob-17",
            authorization_ref="approval:ticket-17", repair_report=regressed,
        )
