"""Target-neutral executable verification artifact model."""
from __future__ import annotations
from dataclasses import dataclass
from .verification_compiler import VerificationAdapter, VerificationPlan


@dataclass(frozen=True)
class VerificationArtifact:
    artifact_id: str
    target: str
    obligation_id: str
    executor_kind: str
    action: str
    expected: str
    evidence_schema: tuple[str, ...]


@dataclass(frozen=True)
class VerificationExecution:
    artifact_id: str
    status: str
    evidence: tuple[str, ...]
    executor: str


def compile_verification_artifacts(
    plan: VerificationPlan,
    adapter: VerificationAdapter,
) -> tuple[VerificationArtifact, ...]:
    artifacts: list[VerificationArtifact] = []
    for obligation in plan.obligations:
        if obligation.category not in adapter.supported_categories:
            raise ValueError(
                f"target {adapter.target} cannot execute category {obligation.category}"
            )
        artifacts.append(VerificationArtifact(
            artifact_id=f"{adapter.target}:{obligation.obligation_id}",
            target=adapter.target,
            obligation_id=obligation.obligation_id,
            executor_kind=adapter.executor_kind,
            action=obligation.scenario,
            expected=obligation.expected,
            evidence_schema=(
                "status",
                "observed_result",
                "assertions",
                "runtime_identity",
            ),
        ))
    return tuple(artifacts)


def record_execution(
    artifact: VerificationArtifact,
    status: str,
    observed_result: str,
    assertions: tuple[str, ...] = (),
    runtime_identity: str = "",
) -> VerificationExecution:
    if status not in {"passed", "failed", "blocked"}:
        raise ValueError("status must be passed, failed, or blocked")
    if not runtime_identity:
        raise ValueError("runtime_identity is required for executable evidence")
    evidence = (
        f"observed_result={observed_result}",
        f"assertions={list(assertions)}",
        f"runtime_identity={runtime_identity}",
    )
    return VerificationExecution(
        artifact.artifact_id, status, evidence, artifact.executor_kind
    )
