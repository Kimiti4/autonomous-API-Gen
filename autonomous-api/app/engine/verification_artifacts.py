"""Target-neutral executable verification artifact model."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Sequence
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


@dataclass(frozen=True)
class VerifiedOutputArtifact:
    path: str
    digest: str
    size_bytes: int


@dataclass(frozen=True)
class VerificationArtifactResult:
    verification_id: str
    passed: bool
    artifacts: tuple[VerifiedOutputArtifact, ...]
    missing: tuple[str, ...]
    artifact_digest: str


def collect_verification_outputs(
    result,
    *,
    root: str,
    expected_paths: Sequence[str],
) -> VerificationArtifactResult:
    """Hash expected output files and require every declared output to exist."""
    base = Path(root).resolve()
    artifacts = []
    missing = []

    for relative in expected_paths:
        target = (base / relative).resolve()
        if base not in target.parents:
            raise ValueError("verification-artifact-path-escape:" + relative)
        if not target.exists() or not target.is_file():
            missing.append(relative)
            continue
        data = target.read_bytes()
        artifacts.append(
            VerifiedOutputArtifact(
                path=relative,
                digest=hashlib.sha256(data).hexdigest(),
                size_bytes=len(data),
            )
        )

    ordered = tuple(sorted(artifacts, key=lambda a: a.path))
    payload = "|".join(
        f"{a.path}:{a.digest}:{a.size_bytes}" for a in ordered
    )
    artifact_digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    return VerificationArtifactResult(
        verification_id=result.verification_id,
        passed=result.passed and not missing,
        artifacts=ordered,
        missing=tuple(sorted(missing)),
        artifact_digest=artifact_digest,
    )
