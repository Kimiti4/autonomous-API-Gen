"""Policy boundary for ESAP bounded execution."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class ExecutionPolicy:
    allowed_commands: tuple[str, ...]
    allowed_environment: tuple[str, ...] = ()
    max_timeout_seconds: float = 300.0
    max_output_bytes: int = 1_000_000

    def validate(self) -> None:
        if self.max_timeout_seconds <= 0:
            raise ValueError("execution-policy-invalid-timeout")
        if self.max_output_bytes <= 0:
            raise ValueError("execution-policy-invalid-output-limit")
        if not self.allowed_commands:
            raise ValueError("execution-policy-empty-command-allowlist")


def validate_execution_environment(
    requested_environment: Mapping[str, str] | None = None,
    *,
    policy: ExecutionPolicy,
) -> dict[str, str] | None:
    policy.validate()
    if requested_environment is None:
        return None

    allowed = set(policy.allowed_environment)
    unexpected = sorted(set(requested_environment) - allowed)
    if unexpected:
        raise ValueError(
            "execution-policy-environment-not-allowed:" + ",".join(unexpected)
        )
    return dict(requested_environment)


def validate_command(
    command: Sequence[str],
    *,
    policy: ExecutionPolicy,
    timeout_seconds: float,
) -> None:
    policy.validate()
    if not command or not command[0]:
        raise ValueError("execution-policy-missing-command")
    if command[0] not in set(policy.allowed_commands):
        raise ValueError("execution-policy-command-not-allowed:" + command[0])
    if timeout_seconds > policy.max_timeout_seconds:
        raise ValueError("execution-policy-timeout-exceeded")
