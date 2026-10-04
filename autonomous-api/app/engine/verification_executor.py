"""Governed verification operations built on ESAP bounded execution."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Sequence

from .bounded_execution import ExecutionResult, ExecutionSpec, execute_bounded
from .execution_evidence import ExecutionEvidence, materialize_execution_evidence
from .execution_policy import ExecutionPolicy


class VerificationKind(str, Enum):
    BUILD = "BUILD"
    TEST = "TEST"
    LINT = "LINT"
    TYPECHECK = "TYPECHECK"
    SMOKE_TEST = "SMOKE_TEST"


@dataclass(frozen=True)
class VerificationSpec:
    verification_id: str
    workspace_id: str
    kind: VerificationKind
    command: tuple[str, ...]
    timeout_seconds: float


@dataclass(frozen=True)
class VerificationResult:
    verification_id: str
    workspace_id: str
    kind: VerificationKind
    passed: bool
    execution: ExecutionResult
    evidence: ExecutionEvidence


def execute_verification_operation(
    spec: VerificationSpec,
    *,
    root: str,
    policy: ExecutionPolicy,
) -> VerificationResult:
    if not spec.verification_id:
        raise ValueError("verification-missing-id")
    if not spec.workspace_id:
        raise ValueError("verification-missing-workspace")
    if not spec.command:
        raise ValueError("verification-missing-command")

    execution = execute_bounded(
        ExecutionSpec(
            execution_id=spec.verification_id,
            workspace_id=spec.workspace_id,
            command=spec.command,
            timeout_seconds=spec.timeout_seconds,
        ),
        root=root,
        allowed_commands=policy.allowed_commands,
        policy=policy,
    )
    evidence = materialize_execution_evidence(execution, policy)
    passed = evidence.status == "PASS"

    return VerificationResult(
        verification_id=spec.verification_id,
        workspace_id=spec.workspace_id,
        kind=spec.kind,
        passed=passed,
        execution=execution,
        evidence=evidence,
    )


def execute_verification_suite(
    specs: Sequence[VerificationSpec],
    *,
    root: str,
    policies: Mapping[VerificationKind, ExecutionPolicy],
) -> tuple[VerificationResult, ...]:
    results = []
    for spec in specs:
        policy = policies.get(spec.kind)
        if policy is None:
            raise ValueError("verification-missing-policy:" + spec.kind.value)
        results.append(
            execute_verification_operation(spec, root=root, policy=policy)
        )
    return tuple(results)
