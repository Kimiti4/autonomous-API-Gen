"""Requirement-to-implementation traceability certification.

Every MUST obligation must have a concrete implementation trace, verification
trace and evidence requirement. Missing mappings remain unresolved.
"""
from __future__ import annotations
from dataclasses import dataclass

from .implementation_traceability import ImplementationTracePlan


@dataclass(frozen=True)
class TraceabilityFinding:
    obligation_id: str
    reason: str


@dataclass(frozen=True)
class TraceabilityResult:
    checked: tuple[str, ...]
    findings: tuple[TraceabilityFinding, ...]

    @property
    def complete(self) -> bool:
        return not self.findings


def certify_traceability(
    required_obligation_ids: tuple[str, ...],
    plan: ImplementationTracePlan,
) -> TraceabilityResult:
    traces={t.obligation_id:t for t in plan.traces}
    findings=[]
    for oid in sorted(set(required_obligation_ids)):
        trace=traces.get(oid)
        if trace is None:
            findings.append(TraceabilityFinding(oid,"missing-implementation-trace"))
            continue
        if not trace.component_ids:
            findings.append(TraceabilityFinding(oid,"missing-components"))
        if not trace.implementation_ids:
            findings.append(TraceabilityFinding(oid,"missing-implementation"))
        if not trace.verification_ids:
            findings.append(TraceabilityFinding(oid,"missing-verification-trace"))
        if not trace.evidence_requirements:
            findings.append(TraceabilityFinding(oid,"missing-evidence-requirement"))
        if trace.status != "planned":
            findings.append(TraceabilityFinding(oid,"invalid-trace-status"))
    return TraceabilityResult(tuple(sorted(set(required_obligation_ids))),tuple(findings))


def require_traceability(result: TraceabilityResult) -> None:
    if not result.complete:
        raise ValueError("requirement-traceability-not-certified")
