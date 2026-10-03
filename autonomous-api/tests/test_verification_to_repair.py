from app.engine.verification_to_repair import *
from app.engine.verification_plans import GateResult, VerificationReport

def report(passed=False):
    return VerificationReport(
        "m1",
        (GateResult("backend:api-contract","api-contract",passed,("trace",)),
         GateResult("backend:effect-safety","effect-safety",False,("effect-trace",))),
        passed)

def test_failed_gate_becomes_counterexample():
    g=failed_gates(report())[0]
    # first gate is deliberately failed
    x=gate_to_counterexample(report(),g)
    assert x.counterexample.counterexample_id=="verify:m1:backend:api-contract"
    assert x.counterexample.domain=="backend"

def test_passed_gate_rejected():
    g=report(True).results[0]
    try:
        gate_to_counterexample(report(True),g)
    except ValueError as e:
        assert str(e)=="passed-gate-is-not-counterexample"
        return
    assert False

def test_missing_evidence_rejected():
    r=VerificationReport("m1",(GateResult("backend:effect-safety","effect-safety",False,()),),False)
    try:
        gate_to_counterexample(r,r.results[0])
    except ValueError as e:
        assert str(e)=="counterexample-requires-evidence"
        return
    assert False

def test_repair_candidate_has_hypothesis():
    r=report()
    g=r.results[0]
    candidate=create_repair_candidate(r,g)
    assert candidate.regression_gate_id=="backend:api-contract"
    assert candidate.hypothesis.target_properties==("api-contract",)

def test_gate_must_belong_to_report():
    r=report()
    g=GateResult("security:auth","authorization",False,("e",))
    try:
        gate_to_counterexample(r,g)
    except ValueError as e:
        assert str(e)=="gate-not-in-report"
        return
    assert False
