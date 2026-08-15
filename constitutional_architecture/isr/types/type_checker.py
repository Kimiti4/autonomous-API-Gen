"""
Type Checker.

Performs semantic analysis on the ISR graph, analogous to a compiler's
type checking phase. Validates all edges against the architectural type system.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from constitutional_architecture.isr.graph.typed_graph import TypedGraph
from constitutional_architecture.isr.model.nodes import NodeType
from constitutional_architecture.isr.types.type_system import ArchitecturalTypeSystem, TypeViolation


@dataclass
class TypeCheckResult:
    """Result of type checking an ISR graph."""

    is_valid: bool
    violations: list[TypeViolation] = field(default_factory=list)
    warnings: list[TypeViolation] = field(default_factory=list)
    nodes_checked: int = 0
    edges_checked: int = 0

    @property
    def error_count(self) -> int:
        return len(self.violations)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)


class TypeChecker:
    """
    Architectural type checker for the ISR.

    Performs semantic analysis analogous to a compiler's type checking phase.
    Validates that all node-edge-node combinations conform to the
    architectural type system.
    """

    def __init__(self, type_system: ArchitecturalTypeSystem | None = None) -> None:
        self._type_system = type_system or ArchitecturalTypeSystem()

    def check(self, graph: TypedGraph) -> TypeCheckResult:
        violations: list[TypeViolation] = []
        warnings: list[TypeViolation] = []
        edges_checked = 0

        for edge in graph.edges():
            edges_checked += 1
            source_node = graph.get_node(edge.source_id)
            target_node = graph.get_node(edge.target_id)

            if source_node is None or target_node is None:
                violations.append(TypeViolation(
                    source_id=edge.source_id,
                    source_type=source_node.node_type if source_node else NodeType.SYSTEM,
                    edge_type=edge.edge_type,
                    target_id=edge.target_id,
                    target_type=target_node.node_type if target_node else NodeType.SYSTEM,
                    message=f"Edge '{edge.id}' references non-existent node",
                ))
                continue

            violation = self._type_system.check_connection(
                source_id=edge.source_id,
                source_type=source_node.node_type,
                edge_type=edge.edge_type,
                target_id=edge.target_id,
                target_type=target_node.node_type,
            )

            if violation is not None:
                if violation.severity == "warning":
                    warnings.append(violation)
                else:
                    violations.append(violation)

        return TypeCheckResult(
            is_valid=len(violations) == 0,
            violations=violations,
            warnings=warnings,
            nodes_checked=graph.node_count,
            edges_checked=edges_checked,
        )
