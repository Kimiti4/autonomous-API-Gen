from app.engine.exploration_engine import (
    ExplorationRequest, generate_strategy_space, require_diversity
)

def test_exploration_generates_distinct_strategy_families():
    r=ExplorationRequest("EV",("correctness","reliability"),minimum_strategies=3)
    s=generate_strategy_space(r)
    assert len({x.family for x in s}) >= 3

def test_forbidden_family_is_not_generated():
    r=ExplorationRequest("EV",("security",),forbidden_assumptions=("family:event_driven",))
    s=generate_strategy_space(r)
    assert all(x.family!="event_driven" for x in s)

def test_diversity_is_explicit():
    r=ExplorationRequest("EV",("security",))
    s=generate_strategy_space(r,("modular_monolith","event_driven","workflow_oriented"))
    assert require_diversity(s,3)
