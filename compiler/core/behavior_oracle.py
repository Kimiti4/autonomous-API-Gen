"""Independent reference evaluator used only to generate behavior test oracles.

This module is not imported by generated applications and is never used to
implement runtime behavior. Its output becomes literal expected values in the
generated test suite.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from compiler.core.plan import CompilationPlan
from isr.core.behavior import Expression, expression_field_refs


def sample_context(expression: Expression, plan: CompilationPlan) -> dict[str, Any]:
    context: dict[str, Any] = {}
    for reference in sorted(expression_field_refs(expression)):
        parts = reference.split(".")
        field_name = parts[-1]
        owner = parts[-2] if len(parts) > 1 else None
        matches = []
        for model in plan.data_models:
            if owner is not None and model.entity_name != owner:
                continue
            for field in model.behavior.fields if model.behavior is not None else ():
                if field.name == field_name:
                    matches.append(field)
        if len(matches) != 1:
            raise ValueError(f"cannot create deterministic test input for field reference {reference!r}")
        field = matches[0]
        kind = field.value_type.value
        if kind in ("money", "decimal"):
            value: Any = "100.00"
        elif kind == "integer":
            value = 100
        elif kind == "boolean":
            value = True
        elif kind == "identifier":
            value = "id-sample"
        elif kind == "date":
            value = "2026-01-01"
        elif kind == "datetime":
            value = "2026-01-01T00:00:00Z"
        else:
            value = "sample"
        context[reference] = value
    return context


def _decimal_if_numeric(value: Any) -> Decimal | None:
    if isinstance(value, bool):
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def reference_evaluate(expression: Expression, context: dict[str, Any]) -> Any:
    """Evaluate the bounded expression AST independently of emitted runtimes."""
    op = expression.op
    if op == "literal":
        return expression.value
    if op == "field":
        if expression.field_ref not in context:
            raise ValueError(f"test oracle lacks field {expression.field_ref!r}")
        return context[expression.field_ref]

    args = [reference_evaluate(arg, context) for arg in expression.args]
    if op == "if_else":
        return args[1] if bool(args[0]) else args[2]
    if op == "and":
        return bool(args[0]) and bool(args[1])
    if op == "or":
        return bool(args[0]) or bool(args[1])
    if op == "not":
        return not bool(args[0])
    if op in {"add", "subtract", "multiply", "divide"}:
        left, right = Decimal(str(args[0])), Decimal(str(args[1]))
        if op == "add":
            return left + right
        if op == "subtract":
            return left - right
        if op == "multiply":
            return left * right
        if right == 0:
            raise ValueError("oracle division by zero")
        return left / right

    left, right = args
    numeric_left = _decimal_if_numeric(left)
    numeric_right = _decimal_if_numeric(right)
    if numeric_left is not None and numeric_right is not None:
        left, right = numeric_left, numeric_right
    if op == "equal":
        return left == right
    if op == "not_equal":
        return left != right
    if op == "less_than":
        return left < right
    if op == "less_or_equal":
        return left <= right
    if op == "greater_than":
        return left > right
    if op == "greater_or_equal":
        return left >= right
    raise ValueError(f"unsupported oracle operator: {op!r}")
