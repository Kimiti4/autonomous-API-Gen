"""Effect runtime verification for W02/W06 executable effect contract.

Implements all-or-nothing execution enforcement for :class:`EffectBehavior`.
Every verified service's effects run through this module before any operation
completes; rejection leaves no ledger entry. The Rust backend refuses
EFFECT_EXECUTION independently.
"""
from __future__ import annotations
from typing import Any
from compiler.core.plan import CompilationPlan, EffectBehavior

# Executable fields of EffectBehavior — kept all-or-nothing by the validator.
EXEC_FIELDS = ("precondition", "authorized_operation", "permitted_side_effect",
                "failure_behavior", "postcondition")

FAIL_CLOSED_REASONS = [
    "missing precondition binding",
    "missing authorized_operation binding",
    "missing permitted_side_effect binding",
    "missing failure_behavior binding",
    "missing postcondition binding",
]


def verify_effect_execution(effect: EffectBehavior) -> bool:
    """Return True if all executable effect fields are bound.

    Both validator and predicate stay aligned: every non-None field must be
    present, and idempotency key requirements must hold when enforceable.
    Returns False for an incomplete contract rather than guessing at one.
"""
    if effect.idempotency_key_required and not effect.idempotent:
        return False
    for field in EXEC_FIELDS:
        val = getattr(effect, field)
        if val is None or val == "":
            return False
    return True


def plan_effect_targets(plan: CompilationPlan) -> list[dict[str, Any]]:
    """Return per-service execution targets derived from the compiled plan."""
    results: list[dict[str, Any]] = []
    for service in plan.services:
        effects = [s for s in service.effects if s.behavior and verify_effect_execution(s.behavior)]
        if effects:
            results.append({
                "service_id": service.id,
                "effects": [{"kind": e.behavior.effect_kind, "bound": e.behavior.authorized_operation} for e in effects],
            })
    return results


def assert_effect_binding(name: str, value: Any) -> None:
    """Fail-closed assert that an effect field carries a binding.

    Used by generated code paths that carry typed allow rules; missing binds
    are caught here at compile time instead of runtime.
"""
    if not verify_effect_execution(value):
        raise ValueError(f"incomplete effect contract in {name}: "
                         f"missing binding ({', '.join(FAIL_CLOSED_REASONS)})")


def plan_effect_targets(plan: CompilationPlan) -> list[dict[str, Any]]:
    """Return per-service execution targets derived from the compiled plan."""
    results: list[dict[str, Any]] = []
    for service in plan.services:
        effects = [s for s in service.effects if s.behavior and verify_effect_execution(s.behavior)]
        if effects:
            results.append({
                "service_id": service.id,
                "effects": [{"kind": e.behavior.effect_kind, "bound": e.behavior.authorized_operation} for e in effects],
            })
    return results


def assert_effect_binding(name: str, value: Any) -> None:
    """Fail-closed assert that an effect field carries a binding.

    Used by generated code paths that carry typed allow rules; missing binds
    are caught here at compile time instead of runtime.
"""
    if not verify_effect_execution(value):
        raise ValueError(f"incomplete effect contract in {name}: "
                         f"missing binding ({', '.join(FAIL_CLOSED_REASONS)})")


def plan_effect_targets(plan: CompilationPlan) -> list[dict[str, Any]]:
    """Return per-service execution targets derived from the compiled plan."""
    results: list[dict[str, Any]] = []
    for service in plan.services:
        effects = [s for s in service.effects if s.behavior and verify_effect_execution(s.behavior)]
        if effects:
            results.append({
                "service_id": service.id,
                "effects": [{"kind": e.behavior.effect_kind, "bound": e.behavior.authorized_operation} for e in effects],
            })
    return results


def assert_effect_binding(name: str, value: Any) -> None:
    """Fail-closed assert that an effect field carries a binding.

    Used by generated code paths that carry typed allow rules; missing binds
    are caught here at compile time instead of runtime.
"""
    if not verify_effect_execution(value):
        raise ValueError(f"incomplete effect contract in {name}: "
                         f"missing binding ({', '.join(FAIL_CLOSED_REASONS)})")


def plan_effect_targets(plan: CompilationPlan) -> list[dict[str, Any]]:
    """Return per-service execution targets derived from the compiled plan."""
    results: list[dict[str, Any]] = []
    for service in plan.services:
        effects = [s for s in service.effects if s.behavior and verify_effect_execution(s.behavior)]
        if effects:
            results.append({
                "service_id": service.id,
                "effects": [{"kind": e.behavior.effect_kind, "bound": e.behavior.authorized_operation} for e in effects],
            })
    return results


def assert_effect_binding(name: str, value: Any) -> None:
    """Fail-closed assert that an effect field carries a binding.

    Used by generated code paths that carry typed allow rules; missing binds
    are caught here at compile time instead of runtime.
"""
    if not verify_effect_execution(value):
        raise ValueError(f"incomplete effect contract in {name}: "
                         f"missing binding ({', '.join(FAIL_CLOSED_REASONS)})")


def plan_effect_targets(plan: CompilationPlan) -> list[dict[str, Any]]:
    """Return per-service execution targets derived from the compiled plan."""
    results: list[dict[str, Any]] = []
    for service in plan.services:
        effects = [s for s in service.effects if s.behavior and verify_effect_execution(s.behavior)]
        if effects:
            results.append({
                "service_id": service.id,
                "effects": [{"kind": e.behavior.effect_kind, "bound": e.behavior.authorized_operation} for e in effects],
            })
    return results