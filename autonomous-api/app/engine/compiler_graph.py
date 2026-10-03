"""Repository/compiler artifact dependency graph primitives.

Keeps architecture-level impact analysis connected to concrete compiler
artifacts without making implementation technology part of architectural truth.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class CompilerArtifact:
    artifact_id: str
    layer: str
    kind: str
    source_authority: str
    implementation_target: str | None = None


@dataclass(frozen=True)
class ArtifactDependency:
    upstream_id: str
    downstream_id: str
    relation: str


@dataclass(frozen=True)
class ArtifactGraph:
    artifacts: tuple[CompilerArtifact, ...]
    dependencies: tuple[ArtifactDependency, ...]


@dataclass(frozen=True)
class ImpactedArtifact:
    artifact_id: str
    reason: str
    path: tuple[str, ...]


def validate_graph(graph: ArtifactGraph) -> tuple[str, ...]:
    ids = {a.artifact_id for a in graph.artifacts}
    errors = []
    for a in graph.artifacts:
        if not a.artifact_id:
            errors.append("missing-artifact-id")
        if a.layer not in {
            "architecture", "frontend-ir", "backend-ir", "data-ir",
            "verification", "deployment", "observability", "documentation",
            "implementation",
        }:
            errors.append(f"unknown-layer:{a.artifact_id}:{a.layer}")
    for d in graph.dependencies:
        if d.upstream_id not in ids:
            errors.append(f"unknown-upstream:{d.upstream_id}")
        if d.downstream_id not in ids:
            errors.append(f"unknown-downstream:{d.downstream_id}")
        if d.upstream_id == d.downstream_id:
            errors.append(f"self-dependency:{d.upstream_id}")
    return tuple(errors)


def downstream_impact(
    graph: ArtifactGraph,
    changed_ids: tuple[str, ...],
) -> tuple[ImpactedArtifact, ...]:
    adjacency: dict[str, list[str]] = {}
    for d in graph.dependencies:
        adjacency.setdefault(d.upstream_id, []).append(d.downstream_id)

    results: list[ImpactedArtifact] = []
    queue = [(x, (x,)) for x in changed_ids]
    seen = set(changed_ids)

    while queue:
        current, path = queue.pop(0)
        for child in sorted(adjacency.get(current, ())):
            if child in seen:
                continue
            seen.add(child)
            child_path = path + (child,)
            results.append(
                ImpactedArtifact(
                    child,
                    f"downstream of changed artifact {current}",
                    child_path,
                )
            )
            queue.append((child, child_path))
    return tuple(results)


def technology_neutral(graph: ArtifactGraph) -> bool:
    """Architecture/IR artifacts may not require an implementation target."""
    for a in graph.artifacts:
        if a.layer in {"architecture", "frontend-ir", "backend-ir", "data-ir"}:
            if a.source_authority == "ISR" and a.implementation_target is not None:
                return False
    return True
