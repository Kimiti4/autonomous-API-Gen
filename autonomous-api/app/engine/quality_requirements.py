"""First-class security, privacy and non-functional requirement gates."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping

from .requirement_ir import RequirementGraph, RequirementKind, RequirementPriority


@dataclass(frozen=True)
class QualityGateResult:
    requirement_ids: tuple[str, ...]
    missing_verification: tuple[str, ...]
    missing_evidence: tuple[str, ...]
    failed: tuple[str, ...]
    passed: bool

    def require_pass(self) -> None:
        if not self.passed:
            raise ValueError("quality-requirements-not-certified")


FIRST_CLASS_KINDS = frozenset({
    RequirementKind.SECURITY,
    RequirementKind.NON_FUNCTIONAL,
    RequirementKind.OPERATIONAL,
    RequirementKind.COMPLIANCE,
})


def evaluate_quality_requirements(
    graph: RequirementGraph,
    verification_results: Mapping[str, Mapping[str, object]],
) -> QualityGateResult:
    requirements = tuple(sorted(
        r.requirement_id for r in graph.requirements.values()
        if r.kind in FIRST_CLASS_KINDS and r.priority is RequirementPriority.MUST
    ))
    missing_v=[]; missing_e=[]; failed=[]
    for rid in requirements:
        result=verification_results.get(rid)
        if not result:
            missing_v.append(rid); continue
        if result.get("passed") is not True:
            failed.append(rid)
        if not result.get("evidence_ids"):
            missing_e.append(rid)
    return QualityGateResult(
        requirements, tuple(missing_v), tuple(missing_e), tuple(sorted(set(failed))),
        not (missing_v or missing_e or failed)
    )
