"""Convert executable verification failures into bounded ESAP repair requests."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Sequence, Any

from .fullstack_genome import FullStackGenome
from .repair_coevolution import RepairCandidate
from .verification_executor import VerificationResult


@dataclass(frozen=True)
class VerificationFailure:
    verification_id: str
    kind: str
    reason: str
    evidence_digests: tuple[str, ...]


@dataclass(frozen=True)
class VerificationRepairRequest:
    failures: tuple[VerificationFailure, ...]
    candidate: RepairCandidate | None
    rationale: str


def extract_verification_failures(results: Sequence[VerificationResult]) -> tuple[VerificationFailure, ...]:
    failures = []
    for result in results:
        if result.passed:
            continue
        evidence = tuple(sorted(set(
            getattr(result.evidence, "evidence_digest", None)
            for _ in (0,)
        ) - {None}))
        failures.append(
            VerificationFailure(
                result.verification_id,
                result.kind.value,
                result.reason or "verification-failed",
                evidence,
            )
        )
    return tuple(failures)


def build_verification_repair_request(
    results: Sequence[VerificationResult],
    *,
    repair_candidates: Mapping[str, RepairCandidate],
) -> VerificationRepairRequest:
    failures = extract_verification_failures(results)
    if not failures:
        raise ValueError("missing-verification-failure")
    candidates = [
        repair_candidates[f.verification_id]
        for f in failures
        if f.verification_id in repair_candidates
    ]
    candidate = candidates[0] if candidates else None
    if candidate is None:
        raise ValueError("missing-verification-repair-mutation")
    rationale = "repair required by executable verification evidence: " + "; ".join(
        f"{f.verification_id}={f.reason}" for f in failures
    )
    return VerificationRepairRequest(tuple(failures), candidate, rationale)
