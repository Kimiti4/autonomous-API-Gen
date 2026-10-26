"""Predicate for the one effect contract a backend may execute.

Kept separate from capability and authorization modules so those two can
import it without importing each other.
"""
from __future__ import annotations

import re

from isr.core.behavior import EffectBehavior, Expression

_SIDE_EFFECT = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


def _positive_amount(expression: Expression) -> bool:
    return (
        expression.op == "greater_than"
        and expression.args[0].op == "field"
        and expression.args[0].field_ref == "amount"
        and expression.args[1].op == "literal"
        and expression.args[1].value == 0
    )


def _approved_record(expression: Expression) -> bool:
    return (
        expression.op == "equal"
        and expression.args[0].op == "field"
        and expression.args[0].field_ref == "approved"
        and expression.args[1].op == "literal"
        and expression.args[1].value is True
    )


def is_supported_record_contract(behavior: EffectBehavior) -> bool:
    """True only for a local idempotent record whose tests can be derived.

    The expression shape is part of the supported contract. Other formulas
    remain unsupported instead of being shipped with tests that assume the
    wrong fields.
    """
    return (
        behavior.effect_kind == "record"
        and behavior.idempotent
        and behavior.idempotency_key_required
        and behavior.failure_behavior == "reject_without_commit"
        and behavior.precondition is not None
        and behavior.postcondition is not None
        and _positive_amount(behavior.precondition)
        and _approved_record(behavior.postcondition)
        and behavior.authorized_operation is not None
        and behavior.permitted_side_effect is not None
        and _SIDE_EFFECT.fullmatch(behavior.permitted_side_effect) is not None
    )
