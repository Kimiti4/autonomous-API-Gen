import pytest

from app.engine.execution_policy import ExecutionPolicy
from app.engine.verification_executor import (
    VerificationKind, VerificationSpec, execute_verification_suite,
)
from app.engine.verification_acceptance import (
    VerificationAcceptancePolicy, VerificationDisposition, assess_verification_suite,
)
from app.engine.verification_artifacts import collect_verification_outputs


def policies():
    p = ExecutionPolicy(("python",), max_timeout_seconds=5)
    return {kind: p for kind in VerificationKind}


def test_acceptance_requires_all_declared_kinds(tmp_path):
    specs = [
        VerificationSpec("build", "ws", VerificationKind.BUILD,
                         ("python", "-c", "print('ok')"), 2),
    ]
    results = execute_verification_suite(specs, root=str(tmp_path), policies=policies())
    disposition = assess_verification_suite(
        results,
        policy=VerificationAcceptancePolicy(
            required_kinds=("BUILD", "TEST"),
        ),
    )
    assert disposition.disposition is VerificationDisposition.INCOMPLETE


def test_acceptance_fails_on_failed_verification(tmp_path):
    specs = [
        VerificationSpec("build", "ws", VerificationKind.BUILD,
                         ("python", "-c", "raise SystemExit(1)"), 2),
    ]
    results = execute_verification_suite(specs, root=str(tmp_path), policies=policies())
    disposition = assess_verification_suite(
        results,
        policy=VerificationAcceptancePolicy(required_kinds=("BUILD",)),
    )
    assert disposition.disposition is VerificationDisposition.FAIL
    assert disposition.failed_verifications == ("build",)


def test_acceptance_requires_outputs_when_declared(tmp_path):
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist/app.bin").write_bytes(b"app")
    specs = [
        VerificationSpec("build", "ws", VerificationKind.BUILD,
                         ("python", "-c", "print('ok')"), 2),
    ]
    results = execute_verification_suite(specs, root=str(tmp_path), policies=policies())
    artifacts = collect_verification_outputs(
        results[0], root=str(tmp_path), expected_paths=("dist/app.bin",)
    )
    disposition = assess_verification_suite(
        results,
        policy=VerificationAcceptancePolicy(
            required_kinds=("BUILD",),
            require_artifacts_for=("BUILD",),
        ),
        artifact_results=(artifacts,),
    )
    assert disposition.disposition is VerificationDisposition.PASS


def test_timeout_is_failure(tmp_path):
    specs = [
        VerificationSpec("test", "ws", VerificationKind.TEST,
                         ("python", "-c", "import time; time.sleep(.2)"), .01),
    ]
    results = execute_verification_suite(specs, root=str(tmp_path), policies=policies())
    disposition = assess_verification_suite(
        results,
        policy=VerificationAcceptancePolicy(required_kinds=("TEST",)),
    )
    assert disposition.disposition is VerificationDisposition.FAIL
    assert disposition.timed_out_verifications == ("test",)
