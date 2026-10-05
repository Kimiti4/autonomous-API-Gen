"""Regression preservation gate for previously certified requirements.

A change may only be admitted if previously certified requirements remain
verified with fresh evidence. Historical evidence is never reused as current
proof.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class RegressionFinding:
    requirement_id: str
    reason: str


@dataclass(frozen=True)
class RegressionPreservationResult:
    checked_requirement_ids: tuple[str, ...]
    findings: tuple[RegressionFinding, ...]

    @property
    def preserved(self) -> bool:
        return not self.findings


def evaluate_regression_preservation(
    certified_requirement_ids: tuple[str, ...],
    current_verification: Mapping[str, Mapping[str, object]],
) -> RegressionPreservationResult:
    findings=[]
    for rid in sorted(set(certified_requirement_ids)):
        result=current_verification.get(rid)
        if not result:
            findings.append(RegressionFinding(rid,"missing-current-verification"))
            continue
        if result.get("passed") is not True:
            findings.append(RegressionFinding(rid,"regression-verification-failed"))
        if not result.get("evidence_ids"):
            findings.append(RegressionFinding(rid,"missing-current-evidence"))
    return RegressionPreservationResult(
        tuple(sorted(set(certified_requirement_ids))), tuple(findings)
    )


def require_regression_preservation(result: RegressionPreservationResult) -> None:
    if not result.preserved:
        reasons=",".join(f"{f.requirement_id}:{f.reason}" for f in result.findings)
        raise ValueError("regression-preservation-failed:"+reasons)
