"""Pure requirement-graph analysis operations.

These are the *tools* of the constitutional requirement-analysis stage. The
Intent Compiler performs pre-flight structural checks at construction; the
authoritative analysis runs inside the Evolution Engine on the ISR, using the
pure helpers defined here. All functions are deterministic and side-effect
free.
"""

from __future__ import annotations

from collections import Counter

from pydantic import BaseModel, Field

from ..models.requirement_graph import (
    DIRECTED_EDGE_KINDS,
    AnalysisFindings,
    CoverageReport,
    EdgeKind,
    GapFinding,
    RequirementGraph,
)
from ..models.system_model import Priority, SystemModel


def find_orphans(graph: RequirementGraph) -> list[str]:
    """Requirement nodes not referenced by any edge."""
    referenced = {
        endpoint
        for edge in graph.edges
        for endpoint in (edge.source_id, edge.target_id)
    }
    return sorted(node.id for node in graph.nodes if node.id not in referenced)


def detect_cycles(graph: RequirementGraph) -> list[list[str]]:
    """Collect directed cycles over directed edge kinds.

    Each cycle is returned once, rotated so its lexicographically smallest
    node id comes first -- deterministic output for stable evidence.
    """
    adjacency: dict[str, list[str]] = {node.id: [] for node in graph.nodes}
    for edge in graph.edges:
        if edge.kind in DIRECTED_EDGE_KINDS:
            adjacency[edge.source_id].append(edge.target_id)
    for targets in adjacency.values():
        targets.sort()

    WHITE, GRAY, BLACK = 0, 1, 2
    color = {node_id: WHITE for node_id in adjacency}
    stack_path: list[str] = []
    cycles: list[tuple[str, ...]] = []

    def visit(start: str) -> None:
        frames: list[tuple[str, list[str]]] = [(start, adjacency[start][:])]
        color[start] = GRAY
        stack_path.append(start)
        while frames:
            node, neighbors = frames[-1]
            advanced = False
            while neighbors:
                candidate = neighbors.pop(0)
                if color[candidate] == GRAY:
                    cycle_start = stack_path.index(candidate)
                    cycles.append(tuple(stack_path[cycle_start:]))
                elif color[candidate] == WHITE:
                    color[candidate] = GRAY
                    stack_path.append(candidate)
                    frames.append((candidate, adjacency[candidate][:]))
                    advanced = True
                    break
            if not advanced:
                color[node] = BLACK
                stack_path.pop()
                frames.pop()

    for node_id in sorted(adjacency):
        if color[node_id] == WHITE:
            visit(node_id)

    def normalize(cycle: tuple[str, ...]) -> tuple[str, ...]:
        pivot = cycle.index(min(cycle))
        return cycle[pivot:] + cycle[:pivot]

    return [list(c) for c in sorted({normalize(c) for c in cycles})]


def find_asymmetric_conflicts(graph: RequirementGraph) -> list[list[str]]:
    """``conflicts_with`` is semantically symmetric; flag one-sided declarations."""
    conflicts = {
        (edge.source_id, edge.target_id)
        for edge in graph.edges
        if edge.kind is EdgeKind.CONFLICTS_WITH
    }
    asymmetric = sorted(
        {tuple(sorted(pair)) for pair in conflicts if (pair[1], pair[0]) not in conflicts}
    )
    return [list(pair) for pair in asymmetric]


def build_coverage(graph: RequirementGraph) -> CoverageReport:
    connected = {
        endpoint
        for edge in graph.edges
        for endpoint in (edge.source_id, edge.target_id)
    }
    isolated_must = sorted(
        node.id
        for node in graph.nodes
        if node.priority is Priority.MUST and node.id not in connected
    )
    return CoverageReport(
        total_nodes=len(graph.nodes),
        by_kind=dict(Counter(node.kind.value for node in graph.nodes)),
        by_priority=dict(Counter(node.priority.value for node in graph.nodes)),
        isolated_must_nodes=isolated_must,
    )


def analyze(graph: RequirementGraph) -> AnalysisFindings:
    """Run the full static-analysis pass and attach findings to a COPY."""
    findings = AnalysisFindings(
        cycles=detect_cycles(graph),
        orphan_nodes=find_orphans(graph),
        asymmetric_conflicts=find_asymmetric_conflicts(graph),
        coverage=build_coverage(graph),
    )
    # Analysis is a derived view: attach a detached copy so the canonical
    # graph's content_hash (which excludes `analysis`) is unaffected.
    return findings


class CrossReferenceFindings(BaseModel):
    """Traceability between a RequirementGraph and a SystemModel (ISR)."""

    untraced_must_requirements: list[GapFinding] = Field(default_factory=list)
    unknown_trace_references: list[GapFinding] = Field(default_factory=list)
    traced_ratio: float = 0.0


def cross_reference(graph: RequirementGraph, model: SystemModel) -> CrossReferenceFindings:
    """Verify ISR <-> requirements traceability.

    Every MUST functional requirement should be traced by at least one
    business capability; every capability trace must point at a real node.
    """
    index = graph.node_index()
    must_functional = sorted(
        node.id
        for node in graph.nodes
        if node.priority is Priority.MUST and node.kind.value == "functional"
    )
    traced: set[str] = set()
    unknown: list[GapFinding] = []
    for capability in model.capabilities:
        for requirement_id in capability.traced_requirement_ids:
            if requirement_id not in index:
                unknown.append(
                    GapFinding(
                        node_id=capability.id,
                        description=(
                            f"capability '{capability.name}' traces unknown "
                            f"requirement '{requirement_id}'"
                        ),
                    )
                )
            else:
                traced.add(requirement_id)

    untraced = [
        GapFinding(
            node_id=node_id,
            description=(
                f"MUST functional requirement '{node_id}' is not traced by any "
                f"business capability"
            ),
        )
        for node_id in must_functional
        if node_id not in traced
    ]
    ratio = (
        len([n for n in must_functional if n in traced]) / len(must_functional)
        if must_functional
        else 1.0
    )
    return CrossReferenceFindings(
        untraced_must_requirements=untraced,
        unknown_trace_references=unknown,
        traced_ratio=round(ratio, 4),
    )
