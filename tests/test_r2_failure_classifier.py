"""R2 -- FailureObservation contract + deterministic, LLM-free classifier.

These tests classify *synthetic* backend output (no Go/Python toolchain, no
Docker) -- the struct-tag defect (D1) is the canonical seed: a real reproducer
of a BUILD_FAILURE/SYNTAX_FAILURE, ideal for pinning the failure pipeline while
R2.3 selects an ISR-expressible mutation target.
"""
from __future__ import annotations

from tiannara.application.diagnosis.classifier import FailureClassifier, FailureEvidenceInput
from tiannara.domain.models.observation import (
    FailureCategory,
    FailureObservation,
    FailurePhase,
    Severity,
)

_CLASSIFIER = FailureClassifier()


def _go_struct_tag_failure() -> FailureEvidenceInput:
    # The exact D1 defect: malformed Go struct tag surfaced by `go test`.
    return FailureEvidenceInput(
        execution_id="exec-1",
        backend_id="go_hexagonal",
        phase=FailurePhase.BUILD,
        command=("go", "test", "./..."),
        exit_code=1,
        stderr=(
            "go: cannot find module golang.org/x/whatever\n"
            "# github.com/tiannara/order_system/internal/domain\n"
            "internal/domain/models.go:5:40: string not terminated\n"
            "internal/domain/models.go:5:40: syntax error: unexpected literal\n"
        ),
    )


def test_classifier_silently_returns_none_on_success():
    inp = FailureEvidenceInput(
        execution_id="exec-0", backend_id="go_hexagonal",
        phase=FailurePhase.TEST, command=("go", "test", "./..."), exit_code=0,
        stdout="ok\tgithub.com/tiannara/order_system\t0.013s",
    )
    assert _CLASSIFIER.classify(inp) is None


def test_struct_tag_defect_maps_to_syntax_failure():
    obs = _CLASSIFIER.classify(_go_struct_tag_failure())
    assert isinstance(obs, FailureObservation)
    assert obs.category is FailureCategory.SYNTAX_FAILURE
    assert obs.phase is FailurePhase.BUILD
    assert obs.severity is Severity.HIGH
    assert obs.exit_code == 1
    assert obs.backend_id == "go_hexagonal"
    assert 0.0 < obs.confidence <= 1.0
    assert obs.evidence_hash
    assert any("models.go" in d for d in obs.diagnostics)
    assert obs.is_build_time is True


def _dep_failure() -> FailureEvidenceInput:
    return FailureEvidenceInput(
        execution_id="exec-2", backend_id="go_hexagonal", phase=FailurePhase.BUILD,
        command=("go", "build", "./..."), exit_code=1,
        stderr="go: cannot find module golang.org/x/whatever",
    )


def test_dependency_failure_pattern():
    obs = _CLASSIFIER.classify(_dep_failure())
    assert obs.category is FailureCategory.DEPENDENCY_FAILURE


def test_type_failure_pattern():
    inp = FailureEvidenceInput(
        execution_id="exec-3", backend_id="go_hexagonal", phase=FailurePhase.BUILD,
        command=("go", "build", "./..."), exit_code=2,
        stderr=("command-line-arguments\n"
                "./main.go:12:9: cannot use x (variable of type string) as int value"),
    )
    obs = _CLASSIFIER.classify(inp)
    assert obs.category is FailureCategory.TYPE_FAILURE


def test_runtime_connection_failure():
    inp = FailureEvidenceInput(
        execution_id="exec-4", backend_id="go_hexagonal", phase=FailurePhase.RUNTIME,
        command=("go", "run", "./cmd/server"), exit_code=1,
        stderr="listen tcp :8080: bind: address already in use",
        stdout="2024-01-01 serve: starting on :8080",
    )
    obs = _CLASSIFIER.classify(inp)
    assert obs.category is FailureCategory.RUNTIME_FAILURE
    assert obs.is_build_time is False


def test_test_failure_pattern():
    inp = FailureEvidenceInput(
        execution_id="exec-5", backend_id="fastapi_hexagonal", phase=FailurePhase.TEST,
        command=("pytest", "app/tests"), exit_code=1,
        stdout="FAILED app/tests/test_api.py::test_resources_require_auth - AssertionError",
    )
    obs = _CLASSIFIER.classify(inp)
    assert obs.category is FailureCategory.TEST_FAILURE
    assert obs.is_build_time is False


def test_classifier_default_falls_back_without_misclassifying():
    inp = FailureEvidenceInput(
        execution_id="exec-6", backend_id="go_hexagonal", phase=FailurePhase.BUILD,
        command=("go", "build", "./..."), exit_code=1, stderr="exit status 1",
    )
    obs = _CLASSIFIER.classify(inp)
    assert obs.category is FailureCategory.BUILD_FAILURE
    assert obs.severity is Severity.LOW
    assert obs.confidence == 0.4


def test_classifier_is_deterministic_and_content_addressable():
    a = _CLASSIFIER.classify(_go_struct_tag_failure())
    b = _CLASSIFIER.classify(_go_struct_tag_failure())
    assert a is not None and b is not None
    assert a.evidence_hash == b.evidence_hash
    assert a.category == b.category
    # Distinct inputs -> distinct hashes.
    assert a.evidence_hash != _CLASSIFIER.classify(_dep_failure()).evidence_hash


def test_failure_observation_round_trips_through_validation():
    obs = _CLASSIFIER.classify(_go_struct_tag_failure())
    again = FailureObservation.model_validate(obs.model_dump())
    assert again.evidence_hash == obs.evidence_hash


def test_evidence_hash_varies_with_phase():
    base = _go_struct_tag_failure()
    h_build = _CLASSIFIER.classify(base).evidence_hash
    h_test = _CLASSIFIER.classify(FailureEvidenceInput(
        execution_id=base.execution_id, backend_id=base.backend_id,
        phase=FailurePhase.TEST, command=base.command, exit_code=base.exit_code,
        stdout=base.stdout, stderr=base.stderr,
    )).evidence_hash
    assert h_build != h_test


def test_r2_spec_seed_reproduces_d1():
    """The struct-tag defect is a real BUILD_FAILURE -> SYNTAX_FAILURE path."""
    obs = _CLASSIFIER.classify(_go_struct_tag_failure())
    assert obs is not None
    assert obs.category is FailureCategory.SYNTAX_FAILURE
    assert "string not terminated" in obs.stderr_excerpt
