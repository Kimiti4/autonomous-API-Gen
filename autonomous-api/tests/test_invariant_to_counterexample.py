from app.engine.invariant_to_counterexample import *
from app.engine.invariant_contracts import InvariantResult

def test_failed_invariant_becomes_counterexample():
    r=InvariantResult("AUTHZ",False,("sec-test",),"violated")
    x=invariant_violation_to_counterexample(r,"security")
    assert x.counterexample.counterexample_id=="inv:AUTHZ"
    assert x.counterexample.violated_property=="AUTHZ"

def test_passed_invariant_cannot_become_counterexample():
    r=InvariantResult("AUTHZ",True,("sec-test",),"passed")
    try:
        invariant_violation_to_counterexample(r,"security")
    except ValueError as e:
        assert str(e)=="passed-invariant-is-not-counterexample"
        return
    assert False

def test_violation_creates_targeted_repair_case():
    r=InvariantResult("AUTHZ",False,("sec-test",),"violated")
    x=invariant_violation_to_counterexample(r,"security")
    case=create_repair_case(x)
    assert case.hypothesis.target_properties==("AUTHZ",)

def test_violation_without_evidence_is_rejected():
    r=InvariantResult("AUTHZ",False,(),"violated")
    try:
        invariant_violation_to_counterexample(r,"security")
    except ValueError as e:
        assert str(e)=="counterexample-requires-evidence"
        return
    assert False
