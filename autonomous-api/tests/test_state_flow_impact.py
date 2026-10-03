from app.engine.state_flow_impact import *

def test_backend_transition_reaches_related_ui_states():
    t=StateTransition("wallet","pending","confirm","confirmed","authorization")
    deps=(
        UIStateDependency("wallet","Submitting","pending","loading"),
        UIStateDependency("wallet","Success","confirmed","navigation"),
        UIStateDependency("wallet","Success","confirmed","cache"),
    )
    i=analyze_state_transition(t,deps)
    assert i.affected_ui_states==("Submitting","Success")
    assert i.affected_behaviors==("cache","loading","navigation")

def test_state_review_always_considers_failure_and_recovery():
    t=StateTransition("swap","queued","start","running","workflow")
    i=analyze_state_transition(t,())
    assert set(required_ui_review_behaviors(i))=={"loading","error","retry","cache","navigation"}

def test_unrelated_flows_are_not_propagated():
    t=StateTransition("wallet","pending","confirm","confirmed","authorization")
    deps=(UIStateDependency("swap","Running","running","loading"),)
    i=analyze_state_transition(t,deps)
    assert i.affected_ui_states==()

def test_multiple_transitions_produce_traceable_impacts():
    ts=(
        StateTransition("x","a","go","b","auth"),
        StateTransition("x","b","finish","c","auth"),
    )
    r=analyze_transitions(ts,())
    assert len(r.impacts)==2
    assert [x.backend_state for x in r.impacts]==["b","c"]
