"""D4: Token budgeting and priority-ordered context selection."""
import pytest

from tiannara.application.intelligence import (
    MustContextOverflowError,
    TokenBudget,
    plan_context_selection,
)
from pydantic import ValidationError

from tiannara.application.intelligence.tokenizing import CharRatioEstimator
from tiannara.domain.models.context_graph import ContextKind, ContextNode
from tiannara.domain.models.intelligence import TaskKind
from tiannara.domain.models.system_model import Priority


def _node(node_id, priority=Priority.SHOULD, pad=0):
    return ContextNode(
        node_id=node_id,
        kind=ContextKind.CAPABILITY,
        priority=priority,
        title=node_id,
        payload={"summary": "s" + ("x" * pad)},
    )


def test_budget_reserves_must_leave_context_pool():
    budget = TokenBudget(
        total_tokens=1000, output_reserve_tokens=200,
        instruction_reserve_tokens=100, schema_reserve_tokens=50,
    )
    assert budget.context_pool_tokens == 650
    with pytest.raises(ValidationError):
        TokenBudget(
            total_tokens=100, output_reserve_tokens=60,
            instruction_reserve_tokens=30, schema_reserve_tokens=20,
        )


def test_selection_prioritises_must_then_should_then_could():
    estimator = CharRatioEstimator()
    must = _node("m1", Priority.MUST, pad=8)
    should_small = _node("s1", Priority.SHOULD, pad=8)
    should_large = _node("s2", Priority.SHOULD, pad=400)
    could = _node("c1", Priority.COULD, pad=8)
    nodes = [must, should_small, should_large, could]

    pool = sum(estimator.count(n.render()) for n in (must, should_small, could))
    planning = plan_context_selection(nodes, estimator, pool)

    assert planning.included_node_ids == ["m1", "s1", "c1"]
    assert planning.dropped_node_ids == ["s2"]
    assert planning.context_tokens_used == pool


def test_must_overflow_fails_loudly():
    estimator = CharRatioEstimator()
    must = _node("m1", Priority.MUST, pad=64)
    required = estimator.count(must.render())
    with pytest.raises(MustContextOverflowError):
        plan_context_selection([must], estimator, required - 1)


def test_planning_is_deterministic():
    estimator = CharRatioEstimator()
    nodes = [_node("m1", Priority.MUST), _node("s1", Priority.SHOULD, pad=50)]
    first = plan_context_selection(nodes, estimator, 500)
    second = plan_context_selection(nodes, estimator, 500)
    assert first == second
