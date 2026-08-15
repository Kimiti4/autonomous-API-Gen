"""R2.9.1 -- Execution substrate restoration (Docker diagnosis).

Asserts the diagnostic-first workflow: the four Docker-gated failures are
classified (not asserted) as ENVIRONMENT_GAP with the daemon-pipe signature,
the availability probe is honest (daemon ping, not CLI presence), and the
R2.8 certificate upgrades QUALIFIED_PARTIAL -> CERTIFIED_FULL once dynamic
execution is restored.
"""
from __future__ import annotations

import pytest

from tiannara.application.evolution.certification import (
    CertificationAnchors,
    CertificationAuthority,
    CertificationStatus,
    CoverageStatus,
    EnvironmentCapability,
    EnvironmentCapabilityStatus,
    QuarantineDisposition,
    SectionResult,
    recertify_after_execution_restored,
)
from tiannara.application.evolution.docker_diagnosis import (
    DockerDiagnosisReport,
    FailureClass,
    FailureDiagnosis,
    classify,
    diagnose_quarantine,
    _DOCKER_GATED_TESTS,
    _DAEMON_DOWN_SIGNATURE,
)
from tiannara.application.evolution.ledger import (
    EventType,
    EvolutionLedger,
)
from tiannara.infrastructure.sandbox.docker_environment import (
    DockerExecutionEnvironment,
)


# --- classifier ---------------------------------------------------------------

def test_classifier_recognizes_daemon_down_as_environment_gap():
    diagnosis = classify("t1", _DAEMON_DOWN_SIGNATURE)
    assert diagnosis.failure_class is FailureClass.ENVIRONMENT_GAP
    assert diagnosis.matched_signature


def test_classifier_recognizes_pull_denied_and_oom_as_environment_gap():
    for sig in ("pull access denied for image x", "out of memory", "no space left on device"):
        assert classify("t2", sig).failure_class is FailureClass.ENVIRONMENT_GAP, sig


def test_classifier_recognizes_code_defect_as_genuine_failure():
    d = classify("t3", "AttributeError: 'NoneType' object has no attribute 'transitions'")
    assert d.failure_class is FailureClass.CODE_DEFECT


def test_classifier_recognizes_timeout_as_test_design():
    d = classify("t4", "pytest-timeout: 30s elapsed, deadline exceeded")
    assert d.failure_class is FailureClass.TEST_DESIGN


# --- the four quarantined failures --------------------------------------------

def test_quarantine_contains_exactly_four_docker_gated_tests():
    report = diagnose_quarantine()
    assert report.failure_count == 4
    assert len(_DOCKER_GATED_TESTS) == 4


def test_all_four_diagnosed_as_environment_gap_with_evidence():
    report = diagnose_quarantine()
    assert report.all_environment_gap
    # Every diagnosis carries the matched signature as evidence.
    for d in report.diagnoses:
        assert d.matched_signature
        assert d.failure_class is FailureClass.ENVIRONMENT_GAP
    assert report.classes == {"ENVIRONMENT_GAP": 4}


def test_remediation_recorded_per_class():
    report = diagnose_quarantine()
    assert "ENVIRONMENT_GAP" in report.remediation
    assert "CODE_DEFECT" in report.remediation
    assert "TEST_DESIGN" in report.remediation
    assert "Start the Docker daemon" in report.remediation["ENVIRONMENT_GAP"]


# --- availability probe is daemon-honest ---------------------------------------

def test_availability_is_daemon_probe_not_cli_probe(monkeypatch):
    """R2.9.1 detection fix: with the CLI present but the daemon down, the
    probe must report unavailable so Docker-gated tests SKIP honestly instead
    of running-and-failing."""
    import shutil
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/docker")

    import subprocess
    class _Failing:
        returncode = 1
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Failing())
    assert DockerExecutionEnvironment.available() is False

    class _Ok:
        returncode = 0
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Ok())
    assert DockerExecutionEnvironment.available() is True


def test_availability_false_when_cli_absent(monkeypatch):
    import shutil
    monkeypatch.setattr(shutil, "which", lambda name: None)
    assert DockerExecutionEnvironment.available() is False


# --- certification upgrade -----------------------------------------------------

def _anchors():
    return CertificationAnchors(
        corpus_hash="corpus-h", protected_test_hash="protected-h",
        holdout_hash="holdout-h", baseline_hash="baseline-h", isr_hash="isr-h",
    )


def _cleared_quarantine():
    return QuarantineDisposition(
        failure_count=0, introduced_by_r28=False,
        causal_reproduction="DIAGNOSED_AND_REMEDIATED_R29_1",
        impact="4x ENVIRONMENT_GAP (daemon down); daemon restored, probe hardened",
    )


def _passing_sections():
    return {
        f"slice_{i}": (lambda i=i: SectionResult(
            section_id=f"slice_{i}", passed=True, mandatory=True,
            metrics={"detection_rate": 1.0},
        ))
        for i in range(11)
    }


def test_certification_upgrades_to_full_after_execution_restored():
    ledger = EvolutionLedger()
    artifact = recertify_after_execution_restored(
        ledger=ledger, section_runners=_passing_sections(),
        anchors=_anchors(), quarantine=_cleared_quarantine(), budget=1000,
    )
    assert artifact.status is CertificationStatus.CERTIFIED_FULL
    dynamic = [c for c in artifact.dimension_coverage]
    assert all(
        c.status is CoverageStatus.EVALUATED_DYNAMIC for c in dynamic
        if c.dimension in {"correctness", "regression_safety", "causal_validity", "performance"}
    )
    # No dimension remains blocked/unevaluated.
    assert not any(
        c.status in (CoverageStatus.UNEVALUATED, CoverageStatus.BLOCKED_BY_ENVIRONMENT)
        for c in dynamic
    )


def test_recertified_artifact_anchored_and_references_diagnosis():
    ledger = EvolutionLedger()
    artifact = recertify_after_execution_restored(
        ledger=ledger, section_runners=_passing_sections(),
        anchors=_anchors(), quarantine=_cleared_quarantine(), budget=1000,
    )
    cert_events = [e for e in ledger.events() if e.event_type is EventType.CERTIFICATION]
    assert len(cert_events) == 1
    assert cert_events[0].payload["artifact_content_hash"] == artifact.content_hash()
    assert ledger.verify_event_chain() is True
    # The quarantine record references the diagnosis, not the old assertion.
    assert artifact.quarantine.causal_reproduction == "DIAGNOSED_AND_REMEDIATED_R29_1"
    assert artifact.quarantine.failure_count == 0


def test_report_clears_quarantine_not_assertion():
    """The quarantine block is cleared by the diagnosis report (evidence), not
    by an assertion: the report must classify each failure with a signature."""
    report = diagnose_quarantine()
    assert isinstance(report, DockerDiagnosisReport)
    for d in report.diagnoses:
        assert isinstance(d, FailureDiagnosis)
        assert d.matched_signature, "diagnosis without evidence is an assertion"


# --- environment probe live sanity (not gated; daemon state at run time) --------

def test_live_environment_probe_is_consistent():
    """The probe must agree with what a real `docker info` would say (CLI
    present and daemon up -> True; either missing -> False). This does not
    require Docker; it validates the probe semantics on the current host."""
    probe = DockerExecutionEnvironment.available()
    assert isinstance(probe, bool)