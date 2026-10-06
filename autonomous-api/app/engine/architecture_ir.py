"""CAP-002 technology-neutral architecture IR and evaluation.

Architecture candidates describe engineering structure and trade-offs only.
Technology selection remains a downstream compiler concern.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Iterable
from .requirement_isr import EngineeringISR


@dataclass(frozen=True)
class ArchitectureComponent:
    component_id: str
    responsibility: str
    boundary: str
    source_requirements: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__ | {"source_requirements": list(self.source_requirements)}


@dataclass(frozen=True)
class ArchitectureCandidate:
    architecture_id: str
    components: tuple[ArchitectureComponent, ...]
    communication: tuple[str, ...]
    consistency: str
    failure_modes: tuple[str, ...]
    tradeoffs: tuple[str, ...]
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "architecture_id": self.architecture_id,
            "components": [c.to_dict() for c in self.components],
            "communication": list(self.communication),
            "consistency": self.consistency,
            "failure_modes": list(self.failure_modes),
            "tradeoffs": list(self.tradeoffs),
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class ArchitectureEvaluation:
    architecture_id: str
    satisfied_invariants: tuple[str, ...]
    unsatisfied_invariants: tuple[str, ...]
    risks: tuple[str, ...]
    evidence_requirements: tuple[str, ...]
    admissible: bool

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__ | {
            "satisfied_invariants": list(self.satisfied_invariants),
            "unsatisfied_invariants": list(self.unsatisfied_invariants),
            "risks": list(self.risks),
            "evidence_requirements": list(self.evidence_requirements),
        }


def validate_architecture(candidate: ArchitectureCandidate) -> tuple[str, ...]:
    findings: list[str] = []
    if not candidate.components:
        findings.append("architecture has no components")
    if not candidate.rationale.strip():
        findings.append("architecture has no rationale")
    if not candidate.failure_modes:
        findings.append("architecture has no failure modes")
    if not candidate.tradeoffs:
        findings.append("architecture has no explicit trade-offs")
    return tuple(findings)


def evaluate_architecture(candidate: ArchitectureCandidate, isr: EngineeringISR) -> ArchitectureEvaluation:
    findings = list(validate_architecture(candidate))
    component_text = " ".join(
        f"{c.responsibility} {c.boundary}" for c in candidate.components
    ).lower()
    satisfied: list[str] = []
    unsatisfied: list[str] = []
    evidence: list[str] = []

    for invariant in isr.invariants:
        if invariant.statement.lower() in component_text:
            satisfied.append(invariant.invariant_id)
        else:
            unsatisfied.append(invariant.invariant_id)
            evidence.append(f"verify {invariant.invariant_id}: {invariant.statement}")

    if unsatisfied:
        findings.append("one or more ISR invariants lack architectural support")

    return ArchitectureEvaluation(
        candidate.architecture_id, tuple(satisfied), tuple(unsatisfied),
        tuple(findings), tuple(evidence), not findings
    )


def generate_baseline_candidates(isr: EngineeringISR) -> tuple[ArchitectureCandidate, ...]:
    """Produce neutral monolith and separated-boundary candidates.

    This is a baseline generator, not an optimizer. Selection must remain a
    separate governed operation.
    """
    requirements = isr.source_requirement_ids
    monolith = ArchitectureCandidate(
        "ARCH-MONOLITH-001",
        (ArchitectureComponent("COMP-CORE", "cohesive application behavior", "single deployment boundary", requirements),),
        ("in-process calls",), "single consistency boundary",
        ("process failure", "dependency failure"), ("simple operations", "limited independent scaling"),
        "Minimize distributed failure surface while preserving explicit domain boundaries.",
    )
    separated = ArchitectureCandidate(
        "ARCH-BOUNDARIES-001",
        (
            ArchitectureComponent("COMP-DOMAIN", "domain behavior", "domain boundary", requirements),
            ArchitectureComponent("COMP-INTEGRATION", "external communication", "integration boundary", requirements),
        ),
        ("explicit asynchronous or synchronous contracts",), "explicit per-boundary consistency",
        ("network partition", "duplicate delivery", "partial failure"),
        ("independent scaling", "higher operational complexity"),
        "Separate domain and integration concerns to make external failure semantics explicit.",
    )
    return (monolith, separated)
