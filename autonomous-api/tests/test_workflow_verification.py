from app.engine.workflow_execution import *
from app.engine.workflow_graph import WorkflowScenario
from app.engine.workflow_properties import standard_invariants

def scenario():
    return WorkflowScenario("pay:duplicate",("ui","api","backend"),"duplicate-submit")

def valid_runner(s):
    return {
        "passed": True,
        "committed_effect_ids": ["e1"],
        "authorized_effect_ids": ["e1"],
        "final_states": ["confirmed"],
        "valid_states": ["pending","confirmed","failed"],
        "ui_backend_consistent": True,
        "recovery_converged": True,
        "evidence": ["trace-1","assertion-1"],
    }

def duplicate_runner(s):
    o=valid_runner(s)
    o["committed_effect_ids"]=["e1","e1"]
    o["evidence"]=["trace-duplicate"]
    return o

def test_execution_is_not_verified_without_properties():
    r=execute_and_verify(scenario(),valid_runner,())
    assert r.execution_passed
    assert not r.verified

def test_valid_execution_and_properties_are_verified():
    r=execute_and_verify(scenario(),valid_runner,standard_invariants())
    assert r.verified
    assert r.counterexample is None

def test_property_violation_creates_counterexample():
    r=execute_and_verify(scenario(),duplicate_runner,standard_invariants())
    assert not r.verified
    assert r.counterexample is not None
    assert "INV-NO-DUPLICATE-EFFECT" in r.counterexample.violated_assertions
    assert counterexample_is_actionable(r)

def test_counterexample_preserves_execution_evidence():
    r=execute_and_verify(scenario(),duplicate_runner,standard_invariants())
    assert r.counterexample.evidence==("trace-duplicate",)
