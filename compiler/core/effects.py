"""Executable effect contract.

A typed effect is not executable because it names a kind. The only contract a
backend may claim is a local idempotent record: one service binding, one allow
rule, a precondition, and a postcondition. Failure discards the attempt.
External transfers, compensation, and publication recovery stay unsupported.
"""
from __future__ import annotations

from compiler.core.effect_contract import is_supported_record_contract
from compiler.core.plan import CompilationPlan, Effect, Service

__all__ = [
    "assert_record_effects_executable",
    "bound_service",
    "is_supported_record_contract",
    "record_effects",
]


def record_effects(plan: CompilationPlan) -> list[Effect]:
    return [
        effect
        for effect in plan.effects
        if effect.behavior is not None and is_supported_record_contract(effect.behavior)
    ]


def bound_service(plan: CompilationPlan, effect: Effect) -> Service | None:
    services = {service.id: service for service in plan.services}
    owners: list[Service] = []
    seen: set[str] = set()
    for binding in plan.effect_bindings:
        if binding.effect_id != effect.id or binding.source_id not in services:
            continue
        if binding.source_id in seen:
            continue
        seen.add(binding.source_id)
        owners.append(services[binding.source_id])
    if len(owners) != 1:
        return None
    service = owners[0]
    if effect.id not in {item.id for item in service.effects}:
        return None
    return service


def _operation_is_allowed(effect: Effect) -> bool:
    behavior = effect.behavior
    if behavior is None:
        return False
    for policy in effect.security_policies:
        if policy.behavior is None:
            continue
        for rule in policy.behavior.rules:
            if rule.effect != "allow" or not rule.roles:
                continue
            if behavior.authorized_operation not in rule.actions:
                continue
            if rule.resource != behavior.permitted_side_effect:
                continue
            return True
    return False


def assert_record_effects_executable(plan: CompilationPlan) -> None:
    """Refuse a record contract that has no real enforcement point."""
    from compiler.core.capabilities import UnsupportedSemanticsError

    claimed: set[tuple[str, str]] = set()
    for effect in record_effects(plan):
        behavior = effect.behavior
        assert behavior is not None
        service = bound_service(plan, effect)
        if service is None:
            raise UnsupportedSemanticsError(
                f"Effect {effect.id} record contract must be bound to exactly one "
                "service through CAUSES_EFFECT and that service's effect list"
            )
        if not _operation_is_allowed(effect):
            raise UnsupportedSemanticsError(
                f"Effect {effect.id} record contract has no allow rule for "
                f"{behavior.authorized_operation} on {behavior.permitted_side_effect}"
            )
        key = (service.id, behavior.permitted_side_effect)
        if key in claimed:
            raise UnsupportedSemanticsError(
                f"Service {service.id} already executes side effect {behavior.permitted_side_effect}"
            )
        claimed.add(key)
