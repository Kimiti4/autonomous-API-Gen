"""
Architectural Invariants.

Defines invariants that must always hold for a well-formed ISR.
These are checked during validation and must pass before compilation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from constitutional_architecture.isr.graph.typed_graph import TypedGraph
from constitutional_architecture.isr.graph.traversal import GraphTraversal
from constitutional_architecture.isr.model.edges import EdgeType
from constitutional_architecture.isr.model.nodes import NodeType
from constitutional_architecture.isr.validation.diagnostics import Diagnostic, DiagnosticLocation, DiagnosticSeverity


@dataclass(frozen=True)
class InvariantResult:
    """Result of checking a single invariant."""

    invariant_name: str
    passed: bool
    diagnostics: tuple[Diagnostic, ...] = ()


class ArchitecturalInvariants:
    """
    Checks architectural invariants on the ISR graph.

    Invariants are hard constraints that must always hold.
    Violation of any invariant makes the ISR uncompilable.
    """

    @staticmethod
    def check_all(graph: TypedGraph) -> list[InvariantResult]:
        return [
            ArchitecturalInvariants.check_dependency_acyclicity(graph),
            ArchitecturalInvariants.check_unique_identifiers(graph),
            ArchitecturalInvariants.check_referential_integrity(graph),
            ArchitecturalInvariants.check_workflow_reachability(graph),
            ArchitecturalInvariants.check_permission_consistency(graph),
            ArchitecturalInvariants.check_module_has_entities(graph),
        ]

    @staticmethod
    def check_dependency_acyclicity(graph: TypedGraph) -> InvariantResult:
        cycles = GraphTraversal.detect_cycles(graph, EdgeType.DEPENDS_ON)
        if cycles:
            diagnostics = tuple(
                Diagnostic(
                    code="ISR-INV-001",
                    message=f"Circular dependency detected: {' → '.join(cycle)}",
                    severity=DiagnosticSeverity.ERROR,
                    location=DiagnosticLocation(
                        node_id=cycle[0],
                        path=" → ".join(cycle),
                    ),
                    suggested_fix=(
                        "Break the cycle by introducing an interface, "
                        "extracting a shared module, or using event-driven communication."
                    ),
                )
                for cycle in cycles
            )
            return InvariantResult("dependency_acyclicity", False, diagnostics)
        return InvariantResult("dependency_acyclicity", True)

    @staticmethod
    def check_unique_identifiers(graph: TypedGraph) -> InvariantResult:
        seen: dict[tuple[str, NodeType, str | None], str] = {}
        diagnostics: list[Diagnostic] = []

        for node in graph.nodes():
            key = (node.label.lower(), node.node_type, node.parent_id)
            if key in seen and node.label:
                diagnostics.append(Diagnostic(
                    code="ISR-INV-002",
                    message=(
                        f"Duplicate {node.node_type.value} '{node.label}' "
                        f"(IDs: '{seen[key]}' and '{node.id}')"
                    ),
                    severity=DiagnosticSeverity.ERROR,
                    location=DiagnosticLocation(node_id=node.id, node_type=node.node_type.value),
                    suggested_fix="Rename one of the duplicate nodes or merge them.",
                ))
            else:
                seen[key] = node.id

        return InvariantResult("unique_identifiers", len(diagnostics) == 0, tuple(diagnostics))

    @staticmethod
    def check_referential_integrity(graph: TypedGraph) -> InvariantResult:
        diagnostics: list[Diagnostic] = []
        node_ids = {n.id for n in graph.nodes()}

        for edge in graph.edges():
            if edge.source_id not in node_ids:
                diagnostics.append(Diagnostic(
                    code="ISR-INV-003",
                    message=f"Edge '{edge.id}' references non-existent source '{edge.source_id}'",
                    severity=DiagnosticSeverity.ERROR,
                    location=DiagnosticLocation(edge_id=edge.id),
                ))
            if edge.target_id not in node_ids:
                diagnostics.append(Diagnostic(
                    code="ISR-INV-003",
                    message=f"Edge '{edge.id}' references non-existent target '{edge.target_id}'",
                    severity=DiagnosticSeverity.ERROR,
                    location=DiagnosticLocation(edge_id=edge.id),
                ))

        return InvariantResult("referential_integrity", len(diagnostics) == 0, tuple(diagnostics))

    @staticmethod
    def check_workflow_reachability(graph: TypedGraph) -> InvariantResult:
        diagnostics: list[Diagnostic] = []
        workflow_nodes = graph.get_nodes_by_type(NodeType.WORKFLOW)

        for wf_node in workflow_nodes:
            states = [
                n for n in graph.nodes()
                if n.node_type == NodeType.STATE and n.parent_id == wf_node.id
            ]
            if not states:
                continue

            initial_states = [
                s for s in states
                if s.attributes.get("state_type") == "initial"
            ]
            if not initial_states:
                diagnostics.append(Diagnostic(
                    code="ISR-INV-004",
                    message=f"Workflow '{wf_node.label}' has no initial state",
                    severity=DiagnosticSeverity.ERROR,
                    location=DiagnosticLocation(
                        node_id=wf_node.id,
                        node_type="workflow",
                        path=wf_node.label,
                    ),
                    suggested_fix="Add a state with state_type='initial'.",
                ))
                continue

            reachable: set[str] = set()
            for initial in initial_states:
                visited = GraphTraversal.bfs(
                    graph, initial.id,
                    edge_filter=lambda e: e.edge_type == EdgeType.TRANSITIONS_TO,
                )
                reachable.update(n.id for n in visited)

            for state in states:
                if state.id not in reachable:
                    diagnostics.append(Diagnostic(
                        code="ISR-INV-004",
                        message=(
                            f"State '{state.label}' in workflow '{wf_node.label}' "
                            f"is not reachable from any initial state"
                        ),
                        severity=DiagnosticSeverity.WARNING,
                        location=DiagnosticLocation(
                            node_id=state.id,
                            node_type="state",
                            path=f"{wf_node.label} > {state.label}",
                        ),
                        suggested_fix="Add a transition to this state or remove it.",
                    ))

        return InvariantResult("workflow_reachability", len(diagnostics) == 0, tuple(diagnostics))

    @staticmethod
    def check_permission_consistency(graph: TypedGraph) -> InvariantResult:
        diagnostics: list[Diagnostic] = []

        defined_permissions: set[str] = set()
        for node in graph.get_nodes_by_type(NodeType.PERMISSION):
            defined_permissions.add(node.label)

        for node in graph.get_nodes_by_type(NodeType.ENDPOINT):
            required_perms = node.attributes.get("required_permissions", [])
            for perm in required_perms:
                if perm not in defined_permissions:
                    diagnostics.append(Diagnostic(
                        code="ISR-INV-005",
                        message=(
                            f"Endpoint '{node.label}' references undefined "
                            f"permission '{perm}'"
                        ),
                        severity=DiagnosticSeverity.ERROR,
                        location=DiagnosticLocation(
                            node_id=node.id,
                            node_type="endpoint",
                            path=node.label,
                        ),
                        suggested_fix=f"Define permission '{perm}' in a Policy.",
                    ))

        return InvariantResult("permission_consistency", len(diagnostics) == 0, tuple(diagnostics))

    @staticmethod
    def check_module_has_entities(graph: TypedGraph) -> InvariantResult:
        diagnostics: list[Diagnostic] = []
        modules = graph.get_nodes_by_type(NodeType.MODULE)

        for module in modules:
            owned_entities = [
                e for e in graph.get_outgoing_edges(module.id)
                if e.edge_type == EdgeType.OWNS
                and graph.get_node(e.target_id) is not None
                and graph.get_node(e.target_id).node_type == NodeType.ENTITY
            ]
            if not owned_entities:
                diagnostics.append(Diagnostic(
                    code="ISR-INV-006",
                    message=f"Module '{module.label}' owns no entities",
                    severity=DiagnosticSeverity.WARNING,
                    location=DiagnosticLocation(
                        node_id=module.id,
                        node_type="module",
                        path=module.label,
                    ),
                    suggested_fix="Add entities to this module or reconsider its purpose.",
                ))

        return InvariantResult("module_has_entities", True, tuple(diagnostics))
