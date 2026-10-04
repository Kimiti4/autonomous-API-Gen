"""Compile scope-derived verification obligations into executable operations."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Sequence

from .execution_policy import ExecutionPolicy
from .scope_verification import ChangeScope, DerivedVerificationPlan
from .verification_executor import VerificationKind, VerificationSpec


@dataclass(frozen=True)
class VerificationCommandRule:
    kind: VerificationKind
    command: tuple[str, ...]
    timeout_seconds: float
    policy: ExecutionPolicy


@dataclass(frozen=True)
class CompiledVerificationPlan:
    specs: tuple[VerificationSpec, ...]
    policies: Mapping[str, ExecutionPolicy]


def compile_verification_commands(
    plan: DerivedVerificationPlan,
    *,
    workspace_id: str,
    command_rules: Sequence[VerificationCommandRule],
) -> CompiledVerificationPlan:
    by_kind = {rule.kind: rule for rule in command_rules}
    specs: list[VerificationSpec] = []
    policies: dict[str, ExecutionPolicy] = {}

    for kind in plan.required_kinds:
        rule = by_kind.get(kind)
        if rule is None:
            raise ValueError("missing-verification-command:" + kind.value)
        verification_id = f"{workspace_id}:{kind.value.lower()}"
        specs.append(
            VerificationSpec(
                verification_id=verification_id,
                workspace_id=workspace_id,
                kind=kind,
                command=rule.command,
                timeout_seconds=rule.timeout_seconds,
            )
        )
        policies[kind.value] = rule.policy

    return CompiledVerificationPlan(
        specs=tuple(specs),
        policies=policies,
    )
