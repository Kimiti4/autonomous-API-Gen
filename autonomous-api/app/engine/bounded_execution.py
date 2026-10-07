"""Bounded command execution for governed ESAP workspaces."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Mapping, Sequence

from .execution_policy import ExecutionPolicy, validate_command, validate_execution_environment


@dataclass(frozen=True)
class ExecutionSpec:
    execution_id: str
    workspace_id: str
    command: tuple[str, ...]
    timeout_seconds: float
    environment: Mapping[str, str] = None


@dataclass(frozen=True)
class ExecutionResult:
    execution_id: str
    workspace_id: str
    command: tuple[str, ...]
    exit_code: int | None
    timed_out: bool
    stdout: str
    stderr: str
    duration_ms: int
    stdout_digest: str
    stderr_digest: str
    stdout_truncated: bool = False
    stderr_truncated: bool = False


def execute_bounded(
    spec: ExecutionSpec,
    *,
    root: str,
    allowed_commands: Sequence[str],
    policy: ExecutionPolicy | None = None,
) -> ExecutionResult:
    if not spec.execution_id:
        raise ValueError("execution-missing-id")
    if not spec.workspace_id:
        raise ValueError("execution-missing-workspace")
    if not spec.command or not spec.command[0]:
        raise ValueError("execution-missing-command")
    if spec.timeout_seconds <= 0:
        raise ValueError("execution-invalid-timeout")
    if spec.command[0] not in set(allowed_commands):
        raise ValueError("execution-command-not-allowed:" + spec.command[0])

    if policy is not None:
        validate_command(spec.command, policy=policy, timeout_seconds=spec.timeout_seconds)
        env = validate_execution_environment(
            requested_environment=spec.environment, policy=policy
        )
        max_output_bytes = policy.max_output_bytes
    else:
        env = None if spec.environment is None else dict(spec.environment)
        max_output_bytes = None

    base = Path(root).resolve()
    if not base.exists() or not base.is_dir():
        raise ValueError("execution-invalid-root")

    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="esap-exec-") as temp_dir:
        stdout_path = Path(temp_dir) / "stdout"
        stderr_path = Path(temp_dir) / "stderr"
        try:
            with stdout_path.open("wb") as stdout_file, stderr_path.open("wb") as stderr_file:
                completed = subprocess.run(
                    list(spec.command),
                    cwd=base,
                    env=env,
                    stdout=stdout_file,
                    stderr=stderr_file,
                    timeout=spec.timeout_seconds,
                    check=False,
                )
            timed_out = False
            exit_code = completed.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            exit_code = None

        stdout, stdout_truncated = _read_bounded_output(stdout_path, max_output_bytes)
        stderr, stderr_truncated = _read_bounded_output(stderr_path, max_output_bytes)

    duration_ms = int((time.monotonic() - started) * 1000)

    return ExecutionResult(
        execution_id=spec.execution_id,
        workspace_id=spec.workspace_id,
        command=spec.command,
        exit_code=exit_code,
        timed_out=timed_out,
        stdout=stdout,
        stderr=stderr,
        duration_ms=duration_ms,
        stdout_digest=_digest(stdout),
        stderr_digest=_digest(stderr),
        stdout_truncated=stdout_truncated,
        stderr_truncated=stderr_truncated,
    )


def _read_bounded_output(path: Path, max_output_bytes: int | None) -> tuple[str, bool]:
    raw = path.read_bytes()
    if max_output_bytes is None or len(raw) <= max_output_bytes:
        return raw.decode("utf-8", errors="replace"), False
    bounded = raw[:max_output_bytes]
    return bounded.decode("utf-8", errors="replace"), True


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
