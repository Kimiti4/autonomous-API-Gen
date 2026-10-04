import pytest

from app.engine.execution_policy import ExecutionPolicy
from app.engine.transaction_verification import TransactionVerificationConfig, execute_transaction_verification
from app.engine.verification_acceptance import VerificationAcceptancePolicy
from app.engine.verification_executor import VerificationKind, VerificationSpec


def config(command=("python", "-c", "print('ok')")):
    return TransactionVerificationConfig(
        specs=(VerificationSpec("build", "ws", VerificationKind.BUILD, command, 2),),
        policies={"BUILD": ExecutionPolicy(("python",), max_timeout_seconds=5)},
        acceptance=VerificationAcceptancePolicy(required_kinds=("BUILD",)),
        expected_artifacts={},
    )


def test_transaction_verification_returns_pass_with_evidence(tmp_path):
    result = execute_transaction_verification(config(), root=str(tmp_path))
    assert result.disposition.disposition.value == "PASS"
    assert result.evidence_digests


def test_transaction_verification_fails_closed(tmp_path):
    with pytest.raises(ValueError, match="admission-verification-failed"):
        execute_transaction_verification(
            config(("python", "-c", "raise SystemExit(7)")),
            root=str(tmp_path),
        )


def test_transaction_verification_requires_artifact_when_declared(tmp_path):
    required = config()
    required = TransactionVerificationConfig(
        specs=required.specs,
        policies=required.policies,
        acceptance=VerificationAcceptancePolicy(
            required_kinds=("BUILD",), require_artifacts_for=("BUILD",)
        ),
        expected_artifacts={"build": ("dist/app.bin",)},
    )
    with pytest.raises(ValueError, match="admission-incomplete-verification"):
        execute_transaction_verification(required, root=str(tmp_path))
