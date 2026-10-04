"""Bounded command execution for governed ESAP workspaces."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import subprocess
import time
from pathlib import Path
from typing import Mapping, Sequence


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


def execute_bounded(
    spec: ExecutionSpec,
    *,
    root: str,
    allowed_commands: Sequence[str],
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

    base = Path(root).resolve()
    if not base.exists() or not base.is_dir():
        raise ValueError("execution-invalid-root")

    env = None
    if spec.environment is not None:
        env = dict(spec.environment)

    started = time.monotonic()
    try:
        completed = subprocess.run(
            list(spec.command),
            cwd=base,
            env=env,
            capture_output=True,
            text=True,
            timeout=spec.timeout_seconds,
            check=False,
        )
        timed_out = False
        exit_code = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        exit_code = None
        stdout = _decode(exc.stdout)
        stderr = _decode(exc.stderr)
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
    )


def _decode(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
