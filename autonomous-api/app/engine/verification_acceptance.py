"""Acceptance policy and authoritative disposition for ESAP verification."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from .verification_executor import VerificationResult
from .verification_artifacts import VerificationArtifactResult


class VerificationDisposition(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    INCOMPLETE = "INCOMPLETE"


@dataclass(frozen=True)
class VerificationAcceptancePolicy:
    required_kinds: tuple[str, ...]
    require_artifacts_for: tuple[str, ...] = ()
    fail_on_timeout: bool = True


@dataclass(frozen=True)
class VerificationDispositionResult:
    disposition: VerificationDisposition
    required_kinds: tuple[str, ...]
    observed_kinds: tuple[str, ...]
    failed_verifications: tuple[str, ...]
    timed_out_verifications: tuple[str, ...]
    missing_artifacts: tuple[str, ...]


def assess_verification_suite(
    results: Sequence[VerificationResult],
    *,
    policy: VerificationAcceptancePolicy,
    artifact_results: Sequence[VerificationArtifactResult] = (),
) -> VerificationDispositionResult:
    required = tuple(dict.fromkeys(policy.required_kinds))
    observed = tuple(dict.fromkeys(r.kind.value for r in results))

    failed = tuple(sorted(
        r.verification_id for r in results if not r.passed
    ))
    timed_out = tuple(sorted(
        r.verification_id for r in results if r.execution.timed_out
    ))

    artifacts_by_id = {r.verification_id: r for r in artifact_results}
    missing = tuple(sorted({
        path
        for artifact_result in artifact_results
        for path in artifact_result.missing
    }))

    missing_kinds = tuple(kind for kind in required if kind not in observed)
    artifact_required_missing = tuple(
        r.verification_id
        for r in results
        if r.kind.value in policy.require_artifacts_for
        and (
            r.verification_id not in artifacts_by_id
            or not artifacts_by_id[r.verification_id].passed
        )
    )

    if missing_kinds or artifact_required_missing:
        disposition = VerificationDisposition.INCOMPLETE
    elif failed or (policy.fail_on_timeout and timed_out):
        disposition = VerificationDisposition.FAIL
    else:
        disposition = VerificationDisposition.PASS

    return VerificationDispositionResult(
        disposition=disposition,
        required_kinds=required,
        observed_kinds=observed,
        failed_verifications=failed,
        timed_out_verifications=timed_out,
        missing_artifacts=missing,
    )
