import hashlib

import pytest

from app.engine.execution_policy import ExecutionPolicy
from app.engine.verification_executor import VerificationKind, VerificationSpec, execute_verification_operation
from app.engine.verification_artifacts import collect_verification_outputs


def test_success_requires_declared_output_and_hashes_it(tmp_path):
    output = b"artifact"
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist/app.bin").write_bytes(output)
    policy = ExecutionPolicy(("python",), max_timeout_seconds=5)
    result = execute_verification_operation(
        VerificationSpec("v1", "ws", VerificationKind.BUILD,
                         ("python", "-c", "print('built')"), 2),
        root=str(tmp_path), policy=policy,
    )
    collected = collect_verification_outputs(
        result, root=str(tmp_path), expected_paths=("dist/app.bin",)
    )
    assert collected.passed
    assert collected.artifacts[0].digest == hashlib.sha256(output).hexdigest()
    assert collected.missing == ()
    assert len(collected.artifact_digest) == 64


def test_missing_output_prevents_verification_pass(tmp_path):
    policy = ExecutionPolicy(("python",), max_timeout_seconds=5)
    result = execute_verification_operation(
        VerificationSpec("v2", "ws", VerificationKind.BUILD,
                         ("python", "-c", "print('built')"), 2),
        root=str(tmp_path), policy=policy,
    )
    collected = collect_verification_outputs(
        result, root=str(tmp_path), expected_paths=("dist/app.bin",)
    )
    assert not collected.passed
    assert collected.missing == ("dist/app.bin",)


def test_output_path_escape_is_rejected(tmp_path):
    policy = ExecutionPolicy(("python",), max_timeout_seconds=5)
    result = execute_verification_operation(
        VerificationSpec("v3", "ws", VerificationKind.BUILD,
                         ("python", "-c", "print('built')"), 2),
        root=str(tmp_path), policy=policy,
    )
    with pytest.raises(ValueError, match="verification-artifact-path-escape"):
        collect_verification_outputs(
            result, root=str(tmp_path), expected_paths=("../outside",)
        )
