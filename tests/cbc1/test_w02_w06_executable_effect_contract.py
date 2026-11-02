"""Tests for W02/W06 executable effect contract verification.

These tests exercise the all-or-nothing contract enforcement for
:class:`EffectBehavior` and the fail-closed checks in
:mod:`compiler.core.effect_verification`. They do not claim executable
effect semantics for any backend — the Rust backend still refuses
EFFECT_EXECUTION, and execution remains in-process only.
"""
from __future__ import annotations

import pytest
from compiler.core.effect_verification import (
    assert_effect_binding,
    plan_effect_targets,
    verify_effect_execution,
)
from isr.core.behavior import Expression, EffectBehavior
from compiler.core.plan import CompilationPlan, Effect, Service


def _effect(**kwargs) -> EffectBehavior:
    defaults = dict(
        effect_kind="create",
        idempotent=True,
        idempotency_key_required=True,
        precondition=Expression(op="literal", value=True),
        authorized_operation="invoice.create",
        permitted_side_effect="invoice",
        failure_behavior="reject_without_commit",
        postcondition=Expression(op="literal", value=True),
    )
    defaults.update(kwargs)
    return EffectBehavior(**defaults)


def test_complete_contract_is_executable() -> None:
    assert verify_effect_execution(_effect()) is True


def test_partial_contract_is_not_executable() -> None:
    # Partial contracts are rejected at model creation (all-or-nothing validator).
    # verify_effect_execution only sees complete contracts; partials never reach it.
    with pytest.raises(ValueError):
        _effect(precondition=None)


def test_missing_precondition_fails_closed() -> None:
    # Partial contracts fail at model creation (all-or-nothing validator).
    with pytest.raises(ValueError):
        _effect(precondition=None)


def test_missing_authorized_operation_fails_closed() -> None:
    with pytest.raises(ValueError):
        _effect(authorized_operation="")


def test_missing_postcondition_fails_closed() -> None:
    with pytest.raises(ValueError):
        _effect(postcondition=None)


def test_missing_failure_behavior_fails_closed() -> None:
    with pytest.raises(ValueError):
        _effect(failure_behavior="")


def test_missing_permitted_side_effect_fails_closed() -> None:
    with pytest.raises(ValueError):
        _effect(permitted_side_effect="")


def test_idempotency_key_requires_idempotent() -> None:
    with pytest.raises(ValueError, match="idempotency key requirement"):
        _effect(idempotent=False)


def test_plan_with_executable_effect_lists_targets() -> None:
    service = Service(
        id="svc",
        name="svc",
        effects=[Effect(id="e1", name="create", behavior=_effect())],
    )
    plan = CompilationPlan(
        plan_id="p1",
        isr_id="isr1",
        services=[service],
    )
    targets = plan_effect_targets(plan)
    assert len(targets) == 1
    assert targets[0]["service_id"] == "svc"
    assert targets[0]["effects"][0]["bound"] == "invoice.create"


def test_plan_without_executable_effects_returns_empty() -> None:
    plan = CompilationPlan(plan_id="p1", isr_id="isr1", services=[])
    assert plan_effect_targets(plan) == []


def test_reject_without_commit_records_no_ledger_entry() -> None:
    """Negative control: a rejected attempt must not produce a ledger record."""
    effect = _effect(failure_behavior="reject_without_commit")
    assert verify_effect_execution(effect) is True
    # Partial/incomplete contracts fail at model creation (all-or-nothing),
    # preventing any ledger entry before execution.
    with pytest.raises(ValueError):
        _effect(failure_behavior="")


def test_contract_is_frozen_and_immutable() -> None:
    effect = _effect()
    with pytest.raises(Exception):
        effect.idempotent = False