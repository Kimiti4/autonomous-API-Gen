from types import SimpleNamespace

import pytest

from app.engine.admission_verification import (
    materialize_candidate_verification, require_candidate_verification,
)
from app.engine.verification_acceptance import (
    VerificationAcceptancePolicy, VerificationDisposition, assess_verification_suite,
)
from app.engine.execution_policy import ExecutionPolicy
from app.engine.verification_executor import (
    VerificationKind, VerificationSpec, execute_verification_suite,
)


def run_build(tmp_path, command=("python", "-c", "print('ok')")):
    policy = ExecutionPolicy(("python",), max_timeout_seconds=5)
    spec = VerificationSpec("build", "ws", VerificationKind.BUILD, command, 2)
    return execute_verification_suite([spec], root=str(tmp_path), policies={VerificationKind.BUILD: policy})


def test_passing_candidate_requires_and_carries_evidence(tmp_path):
    results = run_build(tmp_path)
    disposition = assess_verification_suite(
        results, policy=VerificationAcceptancePolicy(required_kinds=("BUILD",))
    )
    candidate = materialize_candidate_verification(disposition, results)
    require_candidate_verification(candidate)
    assert candidate.evidence_digests


def test_incomplete_candidate_is_rejected(tmp_path):
    results = run_build(tmp_path)
    disposition = assess_verification_suite(
        results, policy=VerificationAcceptancePolicy(required_kinds=("BUILD", "TEST"))
    )
    candidate = materialize_candidate_verification(disposition, results)
    with pytest.raises(ValueError, match="admission-incomplete-verification"):
        require_candidate_verification(candidate)


def test_failed_candidate_is_rejected(tmp_path):
    results = run_build(tmp_path, ("python", "-c", "raise SystemExit(4)"))
    disposition = assess_verification_suite(
        results, policy=VerificationAcceptancePolicy(required_kinds=("BUILD",))
    )
    candidate = materialize_candidate_verification(disposition, results)
    with pytest.raises(ValueError, match="admission-verification-failed"):
        require_candidate_verification(candidate)
