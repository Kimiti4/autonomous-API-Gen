from app.engine.counterexample_analysis import *

def test_invariant_violations_are_identified():
    assert identify_violations({"safe":True,"no-duplicate":False})==("no-duplicate",)

def test_counterexample_is_shrunk_to_minimal_failing_sequence():
    c=Counterexample("s",("a","noise","b"),("invariant",))
    def fails(actions):
        return "a" in actions and "b" in actions
    m=minimize_counterexample(c,fails)
    assert m.actions==("a","b")
    assert m.removed_actions==("noise",)

def test_deliberation_payload_preserves_evidence_context():
    c=MinimizedCounterexample("s",("a","b"),("invariant",),("noise",))
    p=deliberation_payload(c)
    assert p["minimal_actions"]==("a","b")
    assert p["violated_invariants"]==("invariant",)
