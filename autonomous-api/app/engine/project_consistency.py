"""Project-wide consistency gate.

All certified obligations must remain represented consistently across
architecture, implementation and verification. Missing mappings are unknown,
not inferred as safe.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class ConsistencyFinding:
    obligation_id: str
    reason: str


@dataclass(frozen=True)
class ProjectConsistencyResult:
    checked_obligations: tuple[str, ...]
    findings: tuple[ConsistencyFinding, ...]

    @property
    def consistent(self) -> bool:
        return not self.findings


def evaluate_project_consistency(
    obligation_ids: tuple[str, ...],
    architecture: Mapping[str, object],
    implementation: Mapping[str, object],
    verification: Mapping[str, Mapping[str, object]],
) -> ProjectConsistencyResult:
    findings=[]
    for oid in sorted(set(obligation_ids)):
        if oid not in architecture:
            findings.append(ConsistencyFinding(oid,"missing-architecture-mapping"))
            continue
        if oid not in implementation:
            findings.append(ConsistencyFinding(oid,"missing-implementation-mapping"))
            continue
        result=verification.get(oid)
        if not result:
            findings.append(ConsistencyFinding(oid,"missing-current-verification"))
            continue
        if result.get("passed") is not True:
            findings.append(ConsistencyFinding(oid,"verification-failed"))
        if not result.get("evidence_ids"):
            findings.append(ConsistencyFinding(oid,"missing-current-evidence"))
    return ProjectConsistencyResult(tuple(sorted(set(obligation_ids))),tuple(findings))


def require_project_consistency(result: ProjectConsistencyResult) -> None:
    if not result.consistent:
        raise ValueError("project-consistency-not-certified")
