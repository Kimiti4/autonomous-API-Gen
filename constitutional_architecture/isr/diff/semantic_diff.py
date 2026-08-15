"""
Semantic Diff.

Computes the semantic (architectural decision) difference between two ISR versions.
Unlike structural diff, this identifies WHAT DECISION changed, not just what nodes moved.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from constitutional_architecture.isr.graph.typed_graph import TypedGraph
from constitutional_architecture.isr.diff.structural_diff import StructuralDiff, StructuralDiffResult


@dataclass(frozen=True)
class SemanticChange:
    """A single semantic (architectural decision) change."""

    change_type: str
    description: str
    affected_nodes: tuple[str, ...] = ()
    rationale: str = ""
    fitness_impact: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class SemanticDiffResult:
    """Result of a semantic diff between two ISR versions."""

    changes: tuple[SemanticChange, ...] = ()
    structural_diff: Optional[StructuralDiffResult] = None

    @property
    def change_count(self) -> int:
        return len(self.changes)

    @property
    def summary(self) -> str:
        if not self.changes:
            return "No architectural changes detected."
        return "; ".join(c.description for c in self.changes)


class SemanticDiff:
    """
    Computes semantic architectural differences.

    A structural diff might see "3 edges removed, 2 nodes added."
    A semantic diff identifies: "Decoupled Module A from Module B
    via event-driven communication."
    """

    @staticmethod
    def compute(graph_a: TypedGraph, graph_b: TypedGraph) -> SemanticDiffResult:
        structural = StructuralDiff.compute(graph_a, graph_b)
        changes: list[SemanticChange] = []

        changes.extend(SemanticDiff._detect_module_splits(structural))
        changes.extend(SemanticDiff._detect_event_introduction(structural))
        changes.extend(SemanticDiff._detect_cache_addition(structural))
        changes.extend(SemanticDiff._detect_security_changes(structural))

        if not changes and structural.total_changes > 0:
            changes.append(SemanticChange(
                change_type="structural_modification",
                description=(
                    f"Structural modification: {structural.nodes_added} nodes added, "
                    f"{structural.nodes_removed} removed, "
                    f"{structural.edges_added} edges added, "
                    f"{structural.edges_removed} removed"
                ),
            ))

        return SemanticDiffResult(
            changes=tuple(changes),
            structural_diff=structural,
        )

    @staticmethod
    def _detect_module_splits(diff: StructuralDiffResult) -> list[SemanticChange]:
        changes: list[SemanticChange] = []
        added_modules = [
            c for c in diff.node_changes
            if c.change_type == "added" and c.node.node_type.value == "module"
        ]
        if added_modules:
            for change in added_modules:
                changes.append(SemanticChange(
                    change_type="module_extracted",
                    description=f"Extracted new module '{change.node.label}'",
                    affected_nodes=(change.node.id,),
                ))
        return changes

    @staticmethod
    def _detect_event_introduction(diff: StructuralDiffResult) -> list[SemanticChange]:
        changes: list[SemanticChange] = []
        added_events = [
            c for c in diff.node_changes
            if c.change_type == "added" and c.node.node_type.value == "event"
        ]
        if added_events:
            for change in added_events:
                changes.append(SemanticChange(
                    change_type="event_introduced",
                    description=f"Introduced event '{change.node.label}'",
                    affected_nodes=(change.node.id,),
                ))
        return changes

    @staticmethod
    def _detect_cache_addition(diff: StructuralDiffResult) -> list[SemanticChange]:
        changes: list[SemanticChange] = []
        for change in diff.node_changes:
            if change.change_type == "added" and "cache" in change.node.label.lower():
                changes.append(SemanticChange(
                    change_type="cache_introduced",
                    description=f"Introduced cache '{change.node.label}'",
                    affected_nodes=(change.node.id,),
                ))
        return changes

    @staticmethod
    def _detect_security_changes(diff: StructuralDiffResult) -> list[SemanticChange]:
        changes: list[SemanticChange] = []
        for change in diff.node_changes:
            if change.node.node_type.value == "policy":
                if change.change_type == "added":
                    changes.append(SemanticChange(
                        change_type="policy_added",
                        description=f"Added security policy '{change.node.label}'",
                        affected_nodes=(change.node.id,),
                    ))
                elif change.change_type == "modified":
                    changes.append(SemanticChange(
                        change_type="policy_modified",
                        description=f"Modified security policy '{change.node.label}'",
                        affected_nodes=(change.node.id,),
                    ))
        return changes
