"""Cross-artifact impact analysis for architecture evolution."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class ArtifactRef:
    artifact_type: str
    artifact_id: str


@dataclass(frozen=True)
class ArtifactEdge:
    source: ArtifactRef
    target: ArtifactRef
    relation: str


@dataclass(frozen=True)
class Impact:
    changed: ArtifactRef
    affected: ArtifactRef
    relation: str
    reason: str


@dataclass(frozen=True)
class ImpactReport:
    impacts: tuple[Impact, ...]
    unresolved: tuple[ArtifactRef, ...]


def analyze_impact(
    changes: tuple[ArtifactRef, ...],
    edges: tuple[ArtifactEdge, ...],
) -> ImpactReport:
    changed = set(changes)
    impacts = []
    for edge in edges:
        if edge.source in changed:
            impacts.append(Impact(
                edge.source, edge.target, edge.relation,
                f"source changed; {edge.relation} dependency requires review",
            ))
        if edge.target in changed:
            impacts.append(Impact(
                edge.target, edge.source, f"reverse:{edge.relation}",
                f"target changed; dependent artifact requires review",
            ))
    affected = {i.affected for i in impacts}
    unresolved = tuple(sorted(
        (set(changes) | affected) - changed,
        key=lambda x: (x.artifact_type, x.artifact_id),
    ))
    return ImpactReport(tuple(impacts), unresolved)


def required_review_domains(impact: Impact) -> tuple[str, ...]:
    mapping = {
        "api-contract": ("frontend", "backend", "integration-tests", "documentation"),
        "data-contract": ("backend", "migrations", "analytics", "verification"),
        "state-machine": ("workflow", "frontend", "backend", "verification"),
        "observability": ("operations", "deployment", "verification"),
        "deployment": ("infrastructure", "operations", "security"),
        "security-boundary": ("security", "authorization", "verification"),
    }
    return mapping.get(impact.relation, ("verification",))
