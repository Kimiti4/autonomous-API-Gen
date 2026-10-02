"""Engineering deliberation IR: structured senior-engineering reasoning.

This is not an LLM prompt or a hidden chain-of-thought store. It records the
auditable engineering artifacts Tiannara needs: alternatives, constraints,
trade-offs, risks, falsification tests, decisions, and evidence.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EngineeringConstraint:
    constraint_id: str
    statement: str
    hard: bool = True


@dataclass(frozen=True)
class ArchitectureAlternative:
    alternative_id: str
    summary: str
    benefits: tuple[str, ...] = ()
    costs: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()


@dataclass(frozen=True)
class Tradeoff:
    dimension: str
    alternative_id: str
    consequence: str
    evidence_required: tuple[str, ...] = ()


@dataclass(frozen=True)
class Challenge:
    challenge_id: str
    target: str
    objection: str
    falsification_test: str
    severity: str = "material"


@dataclass(frozen=True)
class EngineeringDeliberation:
    problem: str
    constraints: tuple[EngineeringConstraint, ...]
    alternatives: tuple[ArchitectureAlternative, ...]
    tradeoffs: tuple[Tradeoff, ...]
    challenges: tuple[Challenge, ...]
    unresolved: tuple[str, ...] = ()
    selected_alternative: str | None = None
    selection_rationale: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "problem": self.problem,
            "constraints": [c.__dict__ for c in self.constraints],
            "alternatives": [a.__dict__ for a in self.alternatives],
            "tradeoffs": [t.__dict__ for t in self.tradeoffs],
            "challenges": [c.__dict__ for c in self.challenges],
            "unresolved": list(self.unresolved),
            "selected_alternative": self.selected_alternative,
            "selection_rationale": self.selection_rationale,
        }


def validate_deliberation(d: EngineeringDeliberation) -> tuple[str, ...]:
    findings: list[str] = []
    ids = {a.alternative_id for a in d.alternatives}
    if len(ids) < 2:
        findings.append("engineering deliberation requires at least two alternatives")
    if d.selected_alternative and d.selected_alternative not in ids:
        findings.append("selected alternative is not declared")
    if d.selected_alternative and not d.selection_rationale:
        findings.append("selected alternative requires explicit rationale")
    if not d.challenges:
        findings.append("architecture must have at least one challenge/falsification")
    if any(not t.evidence_required for t in d.tradeoffs):
        findings.append("trade-offs require evidence obligations")
    return tuple(findings)
