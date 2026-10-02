"""Technology-neutral requirements engineering IR for CAP-001.

This module deliberately does not select frameworks, databases or cloud products.
It converts supplied engineering requirements into a deterministic graph that
later compilers/evolution stages can consume and verify.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RequirementKind(str, Enum):
    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non_functional"
    SECURITY = "security"
    OPERATIONAL = "operational"
    COMPLIANCE = "compliance"
    CONSTRAINT = "constraint"


class RequirementPriority(str, Enum):
    MUST = "must"
    SHOULD = "should"
    MAY = "may"


@dataclass(frozen=True)
class AcceptanceCriterion:
    criterion_id: str
    statement: str

    def __post_init__(self) -> None:
        if not self.criterion_id.strip() or not self.statement.strip():
            raise ValueError("acceptance criteria require an id and statement")


@dataclass(frozen=True)
class Requirement:
    requirement_id: str
    statement: str
    kind: RequirementKind
    priority: RequirementPriority = RequirementPriority.MUST
    depends_on: tuple[str, ...] = ()
    conflicts_with: tuple[str, ...] = ()
    acceptance_criteria: tuple[AcceptanceCriterion, ...] = ()
    tags: tuple[str, ...] = ()
    source: str = "user"

    def __post_init__(self) -> None:
        if not self.requirement_id.strip():
            raise ValueError("requirement_id must not be empty")
        if not self.statement.strip():
            raise ValueError("statement must not be empty")


@dataclass(frozen=True)
class RequirementIssue:
    issue_id: str
    severity: str
    requirement_ids: tuple[str, ...]
    message: str


@dataclass
class RequirementGraph:
    requirements: dict[str, Requirement] = field(default_factory=dict)
    issues: list[RequirementIssue] = field(default_factory=list)

    def add(self, requirement: Requirement) -> None:
        if requirement.requirement_id in self.requirements:
            raise ValueError(f"duplicate requirement id: {requirement.requirement_id}")
        self.requirements[requirement.requirement_id] = requirement

    def validate(self) -> list[RequirementIssue]:
        issues: list[RequirementIssue] = []
        ids = set(self.requirements)
        for req in self.requirements.values():
            for dep in req.depends_on:
                if dep not in ids:
                    issues.append(RequirementIssue(
                        f"MISSING-DEP-{req.requirement_id}-{dep}", "error",
                        (req.requirement_id, dep),
                        f"{req.requirement_id} depends on unknown requirement {dep}",
                    ))
            for conflict in req.conflicts_with:
                if conflict not in ids:
                    issues.append(RequirementIssue(
                        f"MISSING-CONFLICT-{req.requirement_id}-{conflict}", "error",
                        (req.requirement_id, conflict),
                        f"{req.requirement_id} conflicts with unknown requirement {conflict}",
                    ))
                elif req.requirement_id in self.requirements[conflict].depends_on:
                    issues.append(RequirementIssue(
                        f"CONTRADICTION-{req.requirement_id}-{conflict}", "error",
                        (req.requirement_id, conflict),
                        "a requirement depends on a requirement it explicitly conflicts with",
                    ))
            if not req.acceptance_criteria:
                issues.append(RequirementIssue(
                    f"NO-AC-{req.requirement_id}", "warning", (req.requirement_id,),
                    "requirement has no explicit acceptance criterion",
                ))
            if req.kind is RequirementKind.NON_FUNCTIONAL and not req.tags:
                issues.append(RequirementIssue(
                    f"AMBIGUOUS-NFR-{req.requirement_id}", "warning", (req.requirement_id,),
                    "non-functional requirement has no measurable/qualifying tags",
                ))
        self.issues = issues
        return list(issues)

    def topological_order(self) -> list[str]:
        self.validate()
        if any(i.severity == "error" for i in self.issues):
            raise ValueError("cannot order an invalid requirement graph")
        incoming = {rid: set(r.depends_on) for rid, r in self.requirements.items()}
        order: list[str] = []
        while incoming:
            ready = sorted(rid for rid, deps in incoming.items() if not deps)
            if not ready:
                raise ValueError("requirement dependency cycle detected")
            order.extend(ready)
            for rid in ready:
                incoming.pop(rid)
            for deps in incoming.values():
                deps.difference_update(ready)
        return order

    def traceability(self) -> dict[str, dict[str, Any]]:
        return {
            rid: {
                "kind": req.kind.value,
                "priority": req.priority.value,
                "acceptance_criteria": [ac.criterion_id for ac in req.acceptance_criteria],
                "depends_on": list(req.depends_on),
                "source": req.source,
            }
            for rid, req in self.requirements.items()
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "CAP-001.v1",
            "requirements": [
                {
                    "requirement_id": r.requirement_id,
                    "statement": r.statement,
                    "kind": r.kind.value,
                    "priority": r.priority.value,
                    "depends_on": list(r.depends_on),
                    "conflicts_with": list(r.conflicts_with),
                    "acceptance_criteria": [
                        {"criterion_id": a.criterion_id, "statement": a.statement}
                        for a in r.acceptance_criteria
                    ],
                    "tags": list(r.tags),
                    "source": r.source,
                }
                for r in self.requirements.values()
            ],
            "issues": [i.__dict__ for i in self.issues],
            "traceability": self.traceability(),
        }


def build_requirement_graph(requirements: list[Requirement]) -> RequirementGraph:
    graph = RequirementGraph()
    for requirement in requirements:
        graph.add(requirement)
    graph.validate()
    return graph


def detect_ambiguity(statement: str) -> list[str]:
    """Return deterministic ambiguity markers; never invent requirements."""
    text = statement.strip().lower()
    markers = []
    vague = ("fast", "secure", "scalable", "robust", "high availability", "user friendly", "soon")
    for word in vague:
        if word in text:
            markers.append(f"unquantified:{word}")
    if not text:
        markers.append("empty")
    return markers
