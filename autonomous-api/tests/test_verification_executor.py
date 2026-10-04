import pytest

from app.engine.execution_policy import ExecutionPolicy
from app.engine.verification_executor import (
    VerificationKind,
    VerificationSpec,
    execute_verification_operation,
    execute_verification_suite,
)


def policies():
    p = ExecutionPolicy(("python",), max_timeout_seconds=5)
    return {kind: p for kind in VerificationKind}


def test_build_operation_produces_governed_pass(tmp_path):
    spec = VerificationSpec(
        "verify-build", "ws-1", VerificationKind.BUILD,
        ("python", "-c", "print('build ok')"), 2,
    )
    result = execute_verification_operation(
        spec, root=str(tmp_path), policy=policies()[VerificationKind.BUILD]
    )
    assert result.passed
    assert result.kind is VerificationKind.BUILD
    assert result.evidence.status == "PASS"


def test_failed_test_operation_is_not_pass(tmp_path):
    spec = VerificationSpec(
        "verify-test", "ws-1", VerificationKind.TEST,
        ("python", "-c", "raise SystemExit(2)"), 2,
    )
    result = execute_verification_operation(
        spec, root=str(tmp_path), policy=policies()[VerificationKind.TEST]
    )
    assert not result.passed
    assert result.evidence.status == "FAIL"


def test_suite_requires_policy_for_every_operation(tmp_path):
    spec = VerificationSpec(
        "verify-lint", "ws-1", VerificationKind.LINT,
        ("python", "-c", "print('lint')"), 2,
    )
    with pytest.raises(ValueError, match="verification-missing-policy:LINT"):
        execute_verification_suite([spec], root=str(tmp_path), policies={})


def test_suite_preserves_operation_order(tmp_path):
    specs = [
        VerificationSpec(
            "build", "ws-1", VerificationKind.BUILD,
            ("python", "-c", "print('b')"), 2,
        ),
        VerificationSpec(
            "test", "ws-1", VerificationKind.TEST,
            ("python", "-c", "print('t')"), 2,
        ),
    ]
    results = execute_verification_suite(specs, root=str(tmp_path), policies=policies())
    assert [r.kind for r in results] == [VerificationKind.BUILD, VerificationKind.TEST]
