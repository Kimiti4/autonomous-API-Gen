import pytest
from app.engine.counterexample_generation import generate_counterexample

def test_generates_evidence_backed_counterexample():
    cx=generate_counterexample(scenario_id="S-1",actions=("login","write"),invariant_results={"auth":False},evidence_ids=("E-1",))
    assert cx.violated_invariants==("auth",)
    assert cx.actions==("login","write")

def test_minimizes_to_smallest_failing_sequence():
    cx=generate_counterexample(scenario_id="S-1",actions=("a","noise","b"),invariant_results={"x":False},evidence_ids=("E-1",),fails=lambda xs: "a" in xs and "b" in xs)
    assert cx.actions==("a","b")
    assert cx.removed_actions==("noise",)

@pytest.mark.parametrize("kwargs",[
    {"scenario_id":"","actions":("a",),"invariant_results":{"x":False},"evidence_ids":("E",)},
    {"scenario_id":"S","actions":(),"invariant_results":{"x":False},"evidence_ids":("E",)},
    {"scenario_id":"S","actions":("a",),"invariant_results":{"x":True},"evidence_ids":("E",)},
    {"scenario_id":"S","actions":("a",),"invariant_results":{"x":False},"evidence_ids":()},
])
def test_generation_fails_closed(kwargs):
    with pytest.raises(ValueError):
        generate_counterexample(**kwargs)
