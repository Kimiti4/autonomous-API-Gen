"""
Main Validation Engine.

Orchestrates all validation passes: type checking, invariant checking,
and custom rule execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from constitutional_architecture.isr.graph.typed_graph import TypedGraph
from constitutional_architecture.isr.types.type_checker import TypeChecker, TypeCheckResult
from constitutional_architecture.isr.validation.diagnostics import Diagnostic, DiagnosticsCollector
from constitutional_architecture.isr.validation.invariants import ArchitecturalInvariants, InvariantResult
from constitutional_architecture.isr.validation.rules import RuleResult, ValidationRule


@dataclass
class ValidationResult:
    """Complete result of ISR validation."""

    is_valid: bool
    type_check: TypeCheckResult
    invariant_results: list[InvariantResult] = field(default_factory=list)
    rule_results: list[RuleResult] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)

    @property
    def all_diagnostics(self) -> list[Diagnostic]:
        all_diags: list[Diagnostic] = list(self.diagnostics)
        for inv in self.invariant_results:
            all_diags.extend(inv.diagnostics)
        for rule in self.rule_results:
            all_diags.extend(rule.diagnostics)
        for violation in self.type_check.violations:
            from constitutional_architecture.isr.validation.diagnostics import (
                DiagnosticLocation,
                DiagnosticSeverity,
            )
            all_diags.append(Diagnostic(
                code="ISR-TYPE-001",
                message=violation.message,
                severity=DiagnosticSeverity.ERROR,
                location=DiagnosticLocation(
                    node_id=violation.source_id,
                    node_type=violation.source_type.value,
                ),
                suggested_fix=violation.suggested_fix,
            ))
        return all_diags

    @property
    def errors(self) -> list[Diagnostic]:
        from constitutional_architecture.isr.validation.diagnostics import DiagnosticSeverity
        return [d for d in self.all_diagnostics if d.severity == DiagnosticSeverity.ERROR]

    @property
    def warnings(self) -> list[Diagnostic]:
        from constitutional_architecture.isr.validation.diagnostics import DiagnosticSeverity
        return [d for d in self.all_diagnostics if d.severity == DiagnosticSeverity.WARNING]


class Validator:
    """
    Main ISR validation engine.

    Orchestrates:
    1. Architectural type checking
    2. Invariant checking
    3. Custom validation rules

    An ISR must pass all validation before it can be compiled.
    """

    def __init__(
        self,
        type_checker: TypeChecker | None = None,
        rules: list[ValidationRule] | None = None,
    ) -> None:
        self._type_checker = type_checker or TypeChecker()
        self._rules = rules or []

    def add_rule(self, rule: ValidationRule) -> None:
        self._rules.append(rule)

    def validate(self, graph: TypedGraph) -> ValidationResult:
        type_result = self._type_checker.check(graph)

        invariant_results = ArchitecturalInvariants.check_all(graph)

        rule_results = [rule.check(graph) for rule in self._rules]

        has_type_errors = not type_result.is_valid
        has_invariant_errors = any(not r.passed for r in invariant_results)
        has_rule_errors = any(not r.passed for r in rule_results)

        is_valid = not has_type_errors and not has_invariant_errors and not has_rule_errors

        return ValidationResult(
            is_valid=is_valid,
            type_check=type_result,
            invariant_results=invariant_results,
            rule_results=rule_results,
        )
