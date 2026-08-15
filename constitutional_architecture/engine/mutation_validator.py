"""
Mutation Validator.

Validates that mutations preserve ISR well-formedness.
Checks preconditions before application and postconditions after.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from constitutional_architecture.engine.mutation_registry import MutationOperatorSpec
from constitutional_architecture.isr.graph.typed_graph import TypedGraph
from constitutional_architecture.isr.types.type_checker import TypeChecker, TypeCheckResult
from constitutional_architecture.isr.validation.validator import Validator, ValidationResult


@dataclass(frozen=True)
class MutationValidationResult:
    is_valid: bool
    preconditions_met: bool = True
    postconditions_met: bool = True
    type_check_passed: bool = True
    invariants_passed: bool = True
    rejection_reason: str = ""
    diagnostics: tuple[str, ...] = ()


class MutationValidator:
    def __init__(
        self,
        validator: Optional[Validator] = None,
        type_checker: Optional[TypeChecker] = None,
    ) -> None:
        self._validator = validator or Validator()
        self._type_checker = type_checker or TypeChecker()

    def check_preconditions(
        self,
        operator: MutationOperatorSpec,
        graph: TypedGraph,
        target_id: str,
    ) -> bool:
        if operator.precondition_fn is not None:
            return operator.precondition_fn(graph, target_id)
        return graph.get_node(target_id) is not None

    def check_postconditions(
        self,
        operator: MutationOperatorSpec,
        graph: TypedGraph,
    ) -> MutationValidationResult:
        type_result: TypeCheckResult = self._type_checker.check(graph)
        if not type_result.is_valid:
            return MutationValidationResult(
                is_valid=False,
                type_check_passed=False,
                rejection_reason=f"Type violations: {type_result.error_count} errors",
                diagnostics=tuple(
                    v.message for v in type_result.violations[:10]
                ),
            )

        validation_result: ValidationResult = self._validator.validate(graph)
        if not validation_result.is_valid:
            return MutationValidationResult(
                is_valid=False,
                invariants_passed=False,
                rejection_reason="Architectural invariant violation",
                diagnostics=tuple(
                    d.message for d in validation_result.errors[:10]
                ),
            )

        if operator.postcondition_fn is not None:
            if not operator.postcondition_fn(graph):
                return MutationValidationResult(
                    is_valid=False,
                    postconditions_met=False,
                    rejection_reason=f"Operator '{operator.identifier}' postcondition failed",
                )

        return MutationValidationResult(is_valid=True)

    def validate_mutation(
        self,
        operator: MutationOperatorSpec,
        source_graph: TypedGraph,
        result_graph: TypedGraph,
        target_id: str,
    ) -> MutationValidationResult:
        if not self.check_preconditions(operator, source_graph, target_id):
            return MutationValidationResult(
                is_valid=False,
                preconditions_met=False,
                rejection_reason=f"Preconditions not met for '{operator.identifier}' on '{target_id}'",
            )

        return self.check_postconditions(operator, result_graph)
