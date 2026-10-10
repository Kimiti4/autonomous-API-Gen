import pytest

from app.engine.deployed_app_observation import (
    DriftSeverity,
    RuntimeDrift,
    RuntimeObservation,
    ObservationStatus,
    assess_deployed_observation,
    require_deployed_maintenance_admission,
)


def observation(**overrides):
    values = dict(
        deployment_id="prod-1",
        observed_revision="abc123",
        environment_fingerprint="env-1",
        status=ObservationStatus.HEALTHY,
        health_evidence=("health:pass",),
        verification_evidence=("smoke:pass",),
        observed_capabilities=("api",),
    )
    values.update(overrides)
    return RuntimeObservation(**values)


def admit(observed=None, **overrides):
    return assess_deployed_observation(
        observed or observation(),
        baseline_revision="abc123",
        baseline_environment_fingerprint="env-1",
        authorized_obligation_ids=("ob-1",),
        explicit_change_authorization=True,
        **overrides,
    )


def test_runtime_observation_is_deterministic_evidence():
    first = observation()
    second = observation()
    assert first.digest == second.digest
    assert first.evidence_complete


def test_digest_uses_unambiguous_structured_encoding():
    first = observation(health_evidence=("a|b", "c"))
    second = observation(health_evidence=("a", "b|c"))
    assert first.digest != second.digest


def test_observation_fails_closed_without_health_evidence():
    with pytest.raises(ValueError, match="missing-health-evidence"):
        observation(health_evidence=())


@pytest.mark.parametrize(
    ("status", "reason"),
    [
        (ObservationStatus.DEGRADED, "runtime-status-not-healthy:degraded"),
        (ObservationStatus.FAILED, "runtime-status-not-healthy:failed"),
        (ObservationStatus.UNKNOWN, "runtime-status-not-healthy:unknown"),
    ],
)
def test_unhealthy_or_unknown_runtime_blocks_maintenance(status, reason):
    admission = admit(observation(status=status))
    assert not admission.executable
    assert reason in admission.reasons


def test_advisory_drift_does_not_create_new_requirement():
    drift = RuntimeDrift(
        "latency-regression",
        DriftSeverity.WARNING,
        "latency exceeded the observation threshold",
        ("metric:latency:123",),
    )
    admission = assess_deployed_observation(
        observation(),
        baseline_revision="abc123",
        baseline_environment_fingerprint="env-1",
        drifts=(drift,),
        authorized_obligation_ids=("ob-1",),
        explicit_change_authorization=True,
    )
    assert admission.executable
    assert "advisory-drift:latency-regression" in admission.reasons


def test_unmapped_drift_cannot_expand_authority():
    drift = RuntimeDrift(
        "auth-regression",
        DriftSeverity.CRITICAL,
        "authentication probe failed",
        ("probe:auth:fail",),
        authoritative_obligation_id="ob-2",
    )
    admission = assess_deployed_observation(
        observation(),
        baseline_revision="abc123",
        baseline_environment_fingerprint="env-1",
        drifts=(drift,),
        authorized_obligation_ids=("ob-1",),
        explicit_change_authorization=True,
    )
    assert not admission.executable
    assert "drift-obligation-not-authorized:auth-regression" in admission.reasons


def test_production_write_requires_deployment_access():
    admission = admit(
        production_write_authorized=True,
        deployment_access=False,
    )
    assert not admission.executable
    assert not admission.production_write_authorized
    assert "production-write-requires-deployment-access" in admission.reasons


def test_production_write_flag_is_not_effective_without_explicit_authorization():
    admission = assess_deployed_observation(
        observation(),
        baseline_revision="abc123",
        baseline_environment_fingerprint="env-1",
        authorized_obligation_ids=("ob-1",),
        explicit_change_authorization=False,
        production_write_authorized=True,
        deployment_access=True,
    )
    assert not admission.executable
    assert not admission.production_write_authorized
    assert "explicit-change-authorization-required" in admission.reasons


def test_missing_change_authorization_blocks_mutation():
    admission = assess_deployed_observation(
        observation(),
        baseline_revision="abc123",
        baseline_environment_fingerprint="env-1",
        authorized_obligation_ids=("ob-1",),
    )
    assert not admission.executable
    with pytest.raises(ValueError, match="explicit-change-authorization-required"):
        require_deployed_maintenance_admission(admission)


def test_runtime_drift_blocks_when_baseline_revision_changes():
    admission = assess_deployed_observation(
        observation(observed_revision="new-revision"),
        baseline_revision="abc123",
        baseline_environment_fingerprint="env-1",
        authorized_obligation_ids=("ob-1",),
        explicit_change_authorization=True,
    )
    assert not admission.executable
    assert "runtime-revision-drift" in admission.reasons


def test_missing_verification_evidence_blocks_maintenance():
    admission = assess_deployed_observation(
        observation(verification_evidence=()),
        baseline_revision="abc123",
        baseline_environment_fingerprint="env-1",
        authorized_obligation_ids=("ob-1",),
        explicit_change_authorization=True,
    )
    assert not admission.executable
    assert "runtime-verification-evidence-incomplete" in admission.reasons
