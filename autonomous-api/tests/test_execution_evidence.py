import pytest

from app.engine.bounded_execution import ExecutionSpec, execute_bounded
from app.engine.execution_evidence import materialize_execution_evidence
from app.engine.execution_policy import ExecutionPolicy


def policy():
    return ExecutionPolicy(
        allowed_commands=("python",),
        allowed_environment=(),
        max_timeout_seconds=5,
        max_output_bytes=1000,
    )


def test_execution_evidence_is_content_addressed(tmp_path):
    p = policy()
    result = execute_bounded(
        ExecutionSpec("exec-1", "ws-1", ("python", "-c", "print('ok')"), 2),
        root=str(tmp_path),
        allowed_commands=p.allowed_commands,
        policy=p,
    )
    evidence = materialize_execution_evidence(result, p)
    assert evidence.status == "PASS"
    assert evidence.exit_code == 0
    assert not evidence.stdout_truncated
    assert not evidence.stderr_truncated
    assert evidence.verify_digest()
    assert len(evidence.evidence_digest) == 64


def test_failed_execution_is_explicitly_recorded(tmp_path):
    p = policy()
    result = execute_bounded(
        ExecutionSpec("exec-2", "ws-1", ("python", "-c", "raise SystemExit(3)"), 2),
        root=str(tmp_path),
        allowed_commands=p.allowed_commands,
        policy=p,
    )
    evidence = materialize_execution_evidence(result, p)
    assert evidence.status == "FAIL"
    assert evidence.exit_code == 3
    assert evidence.verify_digest()


def test_timeout_is_not_reported_as_failure_pass(tmp_path):
    p = policy()
    result = execute_bounded(
        ExecutionSpec("exec-3", "ws-1", ("python", "-c", "import time; time.sleep(0.2)"), 0.01),
        root=str(tmp_path),
        allowed_commands=p.allowed_commands,
        policy=p,
    )
    evidence = materialize_execution_evidence(result, p)
    assert evidence.status == "TIMEOUT"
    assert evidence.timed_out
    assert evidence.verify_digest()


def test_truncation_is_part_of_evidence_digest(tmp_path):
    p = policy()
    result = execute_bounded(
        ExecutionSpec("exec-4", "ws-1", ("python", "-c", "print('x' * 4096)"), 2),
        root=str(tmp_path),
        allowed_commands=p.allowed_commands,
        policy=p,
    )
    evidence = materialize_execution_evidence(result, p)
    assert evidence.stdout_truncated
    assert evidence.verify_digest()
    assert evidence.canonical_payload()["stdout_truncated"] is True
