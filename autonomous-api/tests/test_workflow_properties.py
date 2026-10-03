from app.engine.workflow_properties import *

def test_standard_invariants_pass_for_valid_observation():
    o={
        "committed_effect_ids":["e1"],
        "authorized_effect_ids":["e1"],
        "final_states":["confirmed"],
        "valid_states":["pending","confirmed","failed"],
        "ui_backend_consistent":True,
        "recovery_converged":True,
        "evidence":["trace-1"],
    }
    r=evaluate_properties(o,standard_invariants())
    assert r.passed
    assert len(r.results)==5

def test_duplicate_effect_fails():
    o={"committed_effect_ids":["e1","e1"],"authorized_effect_ids":["e1"],
       "final_states":[],"valid_states":[],"ui_backend_consistent":True,
       "recovery_converged":True}
    r=evaluate_properties(o,standard_invariants())
    assert not next(x for x in r.results if x.assertion_id=="INV-NO-DUPLICATE-EFFECT").passed

def test_unauthorized_effect_fails():
    o={"committed_effect_ids":["e1"],"authorized_effect_ids":[],
       "final_states":[],"valid_states":[],"ui_backend_consistent":True,
       "recovery_converged":True}
    r=evaluate_properties(o,standard_invariants())
    assert not next(x for x in r.results if x.assertion_id=="INV-AUTHORIZATION-PRESERVED").passed

def test_invalid_state_fails():
    o={"committed_effect_ids":[],"authorized_effect_ids":[],
       "final_states":["unknown"],"valid_states":["confirmed"],
       "ui_backend_consistent":True,"recovery_converged":True}
    r=evaluate_properties(o,standard_invariants())
    assert not next(x for x in r.results if x.assertion_id=="INV-STATE-VALID").passed

def test_predicate_error_is_fail_closed():
    a=PropertyAssertion("X","bad",lambda o:o["missing"])
    r=evaluate_properties({},(a,))
    assert not r.passed
    assert r.results[0].reason=="predicate-error:KeyError"
