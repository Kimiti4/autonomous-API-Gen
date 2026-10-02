"""CAP-001 certification gate.

Certification is a completeness claim about the requirements/ISR boundary, not
about implementation quality. Every source requirement must remain traceable;
blocking ambiguity, contradiction, missing dependencies and empty statements
prevent certification.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from .requirement_ir import RequirementGraph
from .requirement_isr import EngineeringISR, project_to_isr


@dataclass(frozen=True)
class CertificationFinding:
    finding_id: str
    severity: str
    message: str
    requirement_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class RequirementCertification:
    capability_id: str
    status: str
    findings: tuple[CertificationFinding, ...]
    source_requirement_count: int
    traced_requirement_count: int
    isr_schema_version: str | None

    @property
    def passed(self) -> bool:
        return self.status == "CERTIFIED"

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "status": self.status,
            "passed": self.passed,
            "source_requirement_count": self.source_requirement_count,
            "traced_requirement_count": self.traced_requirement_count,
            "isr_schema_version": self.isr_schema_version,
            "findings": [f.__dict__ for f in self.findings],
        }


def certify_requirements(graph: RequirementGraph) -> RequirementCertification:
    findings: list[CertificationFinding] = []
    issues = graph.validate()

    for issue in issues:
        findings.append(CertificationFinding(
            issue.issue_id, issue.severity, issue.message, issue.requirement_ids
        ))

    isr: EngineeringISR | None = None
    if not any(f.severity == "error" for f in findings):
        try:
            isr = project_to_isr(graph)
        except ValueError as exc:
            findings.append(CertificationFinding("ISR-PROJECTION", "error", str(exc)))

    if isr is not None:
        source = set(graph.requirements)
        traced = set(isr.traceability)
        missing = sorted(source - traced)
        extra = sorted(traced - source)
        if missing:
            findings.append(CertificationFinding(
                "TRACE-MISSING", "error",
                "ISR is missing source requirement traceability", tuple(missing)
            ))
        if extra:
            findings.append(CertificationFinding(
                "TRACE-EXTRA", "error",
                "ISR contains unknown source requirement traceability", tuple(extra)
            ))
        if len(source) != len(traced):
            findings.append(CertificationFinding(
                "TRACE-COUNT", "error", "ISR/source requirement counts do not match"
            ))

    status = "CERTIFIED" if isr is not None and not any(
        f.severity == "error" for f in findings
    ) else "NOT_CERTIFIED"

    return RequirementCertification(
        "CAP-001", status, tuple(findings), len(graph.requirements),
        len(isr.traceability) if isr else 0,
        isr.schema_version if isr else None,
    )
