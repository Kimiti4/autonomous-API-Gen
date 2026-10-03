"""End-to-end frontend interaction/workflow graph primitives."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class WorkflowNode:
    node_id: str
    kind: str  # ui, action, api, backend, event, persistence, recovery
    name: str


@dataclass(frozen=True)
class WorkflowEdge:
    source_id: str
    target_id: str
    event: str


@dataclass(frozen=True)
class WorkflowGraph:
    workflow_id: str
    nodes: tuple[WorkflowNode, ...]
    edges: tuple[WorkflowEdge, ...]


@dataclass(frozen=True)
class WorkflowScenario:
    scenario_id: str
    node_sequence: tuple[str, ...]
    perturbation: str | None


def validate_workflow(graph: WorkflowGraph) -> tuple[str, ...]:
    ids = {n.node_id for n in graph.nodes}
    errors = []
    for e in graph.edges:
        if e.source_id not in ids:
            errors.append(f"unknown-source:{e.source_id}")
        if e.target_id not in ids:
            errors.append(f"unknown-target:{e.target_id}")
        if e.source_id == e.target_id:
            errors.append(f"self-loop:{e.source_id}")
    return tuple(errors)


def reachable(graph: WorkflowGraph, start_id: str) -> tuple[str, ...]:
    adjacency: dict[str, list[str]] = {}
    for e in graph.edges:
        adjacency.setdefault(e.source_id, []).append(e.target_id)
    seen = {start_id}
    queue = [start_id]
    while queue:
        current = queue.pop(0)
        for child in adjacency.get(current, ()):
            if child not in seen:
                seen.add(child)
                queue.append(child)
    return tuple(sorted(seen))


def derive_failure_scenarios(
    graph: WorkflowGraph,
) -> tuple[WorkflowScenario, ...]:
    normal = tuple(n.node_id for n in graph.nodes)
    scenarios = [
        WorkflowScenario(f"{graph.workflow_id}:timeout", normal, "api-timeout"),
        WorkflowScenario(f"{graph.workflow_id}:retry", normal, "request-retry"),
        WorkflowScenario(f"{graph.workflow_id}:duplicate", normal, "duplicate-submit"),
        WorkflowScenario(f"{graph.workflow_id}:disconnect", normal, "network-disconnect"),
        WorkflowScenario(f"{graph.workflow_id}:backend-failure", normal, "backend-failure"),
        WorkflowScenario(f"{graph.workflow_id}:stale", normal, "stale-client-state"),
    ]
    return tuple(scenarios)
