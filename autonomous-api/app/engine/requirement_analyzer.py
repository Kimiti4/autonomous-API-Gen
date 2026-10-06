"""CAP-001 requirement analysis and decomposition.

The analyzer is intentionally deterministic and evidence-oriented. It extracts
structure from supplied text but never silently resolves ambiguity or invents
requirements. Unresolved findings remain explicit in the engineering graph.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .requirement_ir import (
    AcceptanceCriterion, Requirement, RequirementGraph, RequirementIssue,
    RequirementKind, RequirementPriority, build_requirement_graph,
    detect_ambiguity,
)


@dataclass(frozen=True)
class DecompositionResult:
    graph: RequirementGraph
    unresolved: tuple[RequirementIssue, ...]

    @property
    def ready_for_isr(self) -> bool:
        return not self.unresolved


def classify_statement(statement: str) -> RequirementKind:
    text = statement.lower()
    if any(x in text for x in ("must authenticate", "authenticate", "authorize", "permission", "credential", "secret", "encrypt")):
        return RequirementKind.SECURITY
    if any(x in text for x in ("latency", "throughput", "availability", "uptime", "response time", "within ")):
        return RequirementKind.NON_FUNCTIONAL
    if any(x in text for x in ("deploy", "monitor", "backup", "recover", "alert", "health")):
        return RequirementKind.OPERATIONAL
    if any(x in text for x in ("comply", "compliance", "retention", "regulation", "gdpr")):
        return RequirementKind.COMPLIANCE
    if any(x in text for x in ("must use", "cannot use", "constraint", "only allow")):
        return RequirementKind.CONSTRAINT
    return RequirementKind.FUNCTIONAL


def decompose_statements(statements: Iterable[str], source: str = "user") -> DecompositionResult:
    """Turn supplied atomic-ish statements into a traceable requirement graph.

    No LLM or framework knowledge is required. Each input statement becomes one
    requirement, while ambiguity remains a warning until explicitly resolved.
    """
    statements = list(statements)
    requirements: list[Requirement] = []
    for index, statement in enumerate(statements, 1):
        text = statement.strip()
        rid = f"R-{index:03d}"
        ambiguities = detect_ambiguity(text)
        tags = tuple(ambiguities)
        ac = () if ambiguities else (
            AcceptanceCriterion(f"AC-{index:03d}", f"Observed behavior satisfies: {text}"),
        )
        requirements.append(Requirement(
            requirement_id=rid,
            statement=text,
            kind=classify_statement(text),
            priority=RequirementPriority.MUST,
            acceptance_criteria=ac,
            tags=tags,
            source=source,
        ))
    graph = build_requirement_graph(requirements)
    unresolved = list(graph.issues)
    for index, statement in enumerate(statements, 1):
        for marker in detect_ambiguity(statement):
            issue = RequirementIssue(
                f"AMB-{index:03d}-{marker}", "error", (f"R-{index:03d}",),
                f"unresolved ambiguity: {marker}",
            )
            if issue.issue_id not in {x.issue_id for x in unresolved}:
                unresolved.append(issue)
    graph.issues = unresolved
    return DecompositionResult(graph, tuple(unresolved))


def analyze_requirements(requirements: list[Requirement]) -> DecompositionResult:
    graph = build_requirement_graph(requirements)
    issues = list(graph.issues)
    for req in requirements:
        for marker in detect_ambiguity(req.statement):
            issues.append(RequirementIssue(
                f"AMB-{req.requirement_id}-{marker}", "error",
                (req.requirement_id,), f"unresolved ambiguity: {marker}",
            ))
    # Deterministic de-duplication while retaining first occurrence.
    unique = {issue.issue_id: issue for issue in issues}
    graph.issues = list(unique.values())
    return DecompositionResult(graph, tuple(graph.issues))
