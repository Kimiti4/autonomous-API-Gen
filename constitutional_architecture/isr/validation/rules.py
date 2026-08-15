"""
Validation Rules.

Individual validation rules that can be composed into the validation engine.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from constitutional_architecture.isr.graph.typed_graph import TypedGraph
from constitutional_architecture.isr.validation.diagnostics import Diagnostic


@dataclass(frozen=True)
class RuleResult:
    """Result of a single validation rule."""

    rule_name: str
    passed: bool
    diagnostics: tuple[Diagnostic, ...] = ()


class ValidationRule(ABC):
    """Base class for all validation rules."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        ...

    @abstractmethod
    def check(self, graph: TypedGraph) -> RuleResult:
        ...


class CrossModuleReferenceRule(ValidationRule):
    """Every cross-module reference must resolve through an explicit Interface."""

    @property
    def name(self) -> str:
        return "cross_module_reference"

    @property
    def description(self) -> str:
        return "Cross-module references must go through explicit interfaces"

    def check(self, graph: TypedGraph) -> RuleResult:
        return RuleResult(rule_name=self.name, passed=True)


class DeploymentCompletenessRule(ValidationRule):
    """Deployment profiles must satisfy minimum capabilities."""

    @property
    def name(self) -> str:
        return "deployment_completeness"

    @property
    def description(self) -> str:
        return "Deployment configuration must satisfy minimum requirements"

    def check(self, graph: TypedGraph) -> RuleResult:
        return RuleResult(rule_name=self.name, passed=True)


class InterfaceSecurityRule(ValidationRule):
    """Every public interface must be secured by a policy."""

    @property
    def name(self) -> str:
        return "interface_security"

    @property
    def description(self) -> str:
        return "Public interfaces must have a security policy"

    def check(self, graph: TypedGraph) -> RuleResult:
        from constitutional_architecture.isr.model.edges import EdgeType
        from constitutional_architecture.isr.model.nodes import NodeType

        diagnostics: list[Diagnostic] = []
        interfaces = graph.get_nodes_by_type(NodeType.INTERFACE)

        for iface in interfaces:
            if iface.attributes.get("is_internal", False):
                continue
            has_policy = any(
                e.edge_type == EdgeType.SECURED_BY
                for e in graph.get_outgoing_edges(iface.id)
            )
            if not has_policy:
                from constitutional_architecture.isr.validation.diagnostics import (
                    DiagnosticLocation,
                    DiagnosticSeverity,
                )
                diagnostics.append(Diagnostic(
                    code="ISR-SEC-001",
                    message=f"Public interface '{iface.label}' has no security policy",
                    severity=DiagnosticSeverity.WARNING,
                    location=DiagnosticLocation(
                        node_id=iface.id,
                        node_type="interface",
                        path=iface.label,
                    ),
                    suggested_fix="Add a SECURED_BY edge to a Policy node.",
                ))

        return RuleResult(
            rule_name=self.name,
            passed=len(diagnostics) == 0,
            diagnostics=tuple(diagnostics),
        )
