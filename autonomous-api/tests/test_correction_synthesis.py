from app.engine.correction_synthesis import *
from app.engine.counterexample_analysis import MinimizedCounterexample

def c():
    return MinimizedCounterexample("s",("a","b"),("no-duplicate",),())

def test_multiple_correction_strategies_are_generated():
    xs=synthesize_corrections(c(),("effects-are-concurrent",))
    assert len(xs)==3
    assert {x.strategy for x in xs}=={
        "strengthen-transition-guards",
        "serialize-conflicting-effects",
        "add-compensation-or-recovery",
    }

def test_corrections_preserve_failed_invariants_as_obligations():
    xs=synthesize_corrections(c())
    assert all(x.preserved_invariants==("no-duplicate",) for x in xs)

def test_failure_scope_is_not_overstated():
    assert classify_failure_scope(c(),("effects-are-concurrent",))=="architecture-or-implementation"
    assert classify_failure_scope(c(),())=="implementation"
