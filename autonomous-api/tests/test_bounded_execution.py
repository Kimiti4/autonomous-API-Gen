import pytest

from app.engine.bounded_execution import ExecutionSpec, execute_bounded


def spec(command=("python", "-c", "print('ok')"), timeout=5):
    return ExecutionSpec("exec-1", "ws-1", command, timeout)


def test_executes_allowed_command_and_captures_evidence(tmp_path):
    result = execute_bounded(
        spec(), root=str(tmp_path), allowed_commands=("python",)
    )
    assert result.exit_code == 0
    assert not result.timed_out
    assert result.stdout.strip() == "ok"
    assert len(result.stdout_digest) == 64
    assert len(result.stderr_digest) == 64


def test_rejects_disallowed_command(tmp_path):
    with pytest.raises(ValueError, match="execution-command-not-allowed"):
        execute_bounded(
            spec(("sh", "-c", "echo unsafe")), root=str(tmp_path),
            allowed_commands=("python",),
        )


def test_rejects_invalid_root_and_timeout(tmp_path):
    with pytest.raises(ValueError, match="execution-invalid-root"):
        execute_bounded(spec(), root=str(tmp_path / "missing"), allowed_commands=("python",))
    with pytest.raises(ValueError, match="execution-invalid-timeout"):
        execute_bounded(spec(timeout=0), root=str(tmp_path), allowed_commands=("python",))


def test_timeout_is_recorded_as_bounded_failure(tmp_path):
    result = execute_bounded(
        spec(("python", "-c", "import time; time.sleep(0.2)"), timeout=0.01),
        root=str(tmp_path),
        allowed_commands=("python",),
    )
    assert result.timed_out
    assert result.exit_code is None
