import pytest

from app.engine.deployed_app_observation import (
    ObservationStatus,
    assess_deployed_observation,
    RuntimeObservation,
)
from app.engine.governed_maintenance_record import (
    GovernedMaintenanceRecord,
    validate_maintenance_record,
)


def admitted(**overrides):
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
    values.update(overrides)
    return observation, assess_deployed_observation(observation, **values)


def record(observation_digest, **overrides):
    values = dict(
        observation_digest=observation_digest,
        obligation_id="ob-17",
        patch_digest="sha256:patch-123",
        verification_evidence=("unit:pass", "regression:pass"),
        authorization_ref="approval:ticket-17",
    )
    values.update(overrides)
    return GovernedMaintenanceRecord(**values)


def test_record_links_observation_authorized_obligation_patch_and_verification():
    observation, admission = admitted()
    validate_maintenance_record(record(observation.digest), admission)


def test_record_rejects_different_observation_digest():
    _, admission = admitted()
    with pytest.raises(ValueError, match="observation-digest-mismatch"):
        validate_maintenance_record(record("wrong-digest"), admission)


def test_record_rejects_obligation_outside_authorized_set():
    observation, admission = admitted()
    with pytest.raises(ValueError, match="obligation-not-authorized"):
        validate_maintenance_record(record(observation.digest, obligation_id="ob-99"), admission)


def test_record_rejects_missing_patch_digest():
    observation, admission = admitted()
    with pytest.raises(ValueError, match="missing-patch-digest"):
        validate_maintenance_record(record(observation.digest, patch_digest=""), admission)


def test_record_rejects_missing_verification_evidence():
    observation, admission = admitted()
    with pytest.raises(ValueError, match="missing-verification-evidence"):
        validate_maintenance_record(record(observation.digest, verification_evidence=()), admission)


def test_record_requires_authorization_reference():
    observation, admission = admitted()
    with pytest.raises(ValueError, match="missing-authorization-reference"):
        validate_maintenance_record(record(observation.digest, authorization_ref="  "), admission)


def test_record_rejects_production_write_without_authority():
    observation, admission = admitted()
    candidate = record(observation.digest, production_write_requested=True)
    with pytest.raises(ValueError, match="production-write-not-authorized"):
        validate_maintenance_record(candidate, admission)


def test_record_cannot_bypass_failed_admission():
    observation, admission = admitted(explicit_change_authorization=False)
    with pytest.raises(ValueError, match="maintenance-admission-not-executable"):
        validate_maintenance_record(record(observation.digest), admission)
