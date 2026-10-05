from app.engine.cross_domain_evolution import CoEvolutionEvent, CoEvolutionResult, DomainChange
from app.engine.repair_feedback_loop import run_counterexample_repair_feedback
from app.engine.verification_plans import GateResult, VerificationReport
import pytest

def result(event_id, architecture_id, passed, evidence="e"):
    event = CoEvolutionEvent(event_id, "parent", (DomainChange("backend", "m1", ("safety",)),), ("impact",))
    report = VerificationReport("m1", (GateResult("backend:safety", "safety", passed, (evidence,)),), passed)
    return CoEvolutionResult(event, architecture_id, (report,), passed)

def test_feedback_closes_after_repair():
    calls=[]
    def repair(current, counterexamples, iteration):
        calls.append((iteration, counterexamples[0].failed_properties))
        return result("repair-1", "arch-2", True, "fresh")
    out=run_counterexample_repair_feedback(result("initial","arch-1",False), repair)
    assert out.status=="closed"
    assert len(out.rounds)==2
    assert calls==[(1,("safety",))]

def test_feedback_blocks_repeated_counterexample():
    def repair(current, counterexamples, iteration):
        return result("repair-1","arch-2",False,"fresh")
    out=run_counterexample_repair_feedback(result("initial","arch-1",False),repair)
    assert out.status=="blocked"
    assert out.residuals==("repeated-counterexample-signature",)

def test_feedback_is_bounded():
    def repair(current, counterexamples, iteration):
        return result(f"repair-{iteration}",f"arch-{iteration+1}",False,f"fresh-{iteration}")
    out=run_counterexample_repair_feedback(result("initial","arch-1",False),repair,max_rounds=2)
    assert out.status=="bounded-exhausted"
    assert out.residuals==("maximum-repair-rounds-reached",)
    assert len(out.rounds)==2

def test_feedback_requires_new_event_and_architecture():
    with pytest.raises(ValueError,match="repair-feedback-requires-new-event"):
        run_counterexample_repair_feedback(result("initial","arch-1",False),lambda current,*_:current)
    with pytest.raises(ValueError,match="repair-feedback-requires-new-architecture"):
        run_counterexample_repair_feedback(result("initial","arch-1",False),lambda *_:result("new","arch-1",False,"new"))

def test_feedback_fails_closed_without_counterexample():
    event=CoEvolutionEvent("evt","parent",(DomainChange("backend","m1",("safety",)),),("impact",))
    report=VerificationReport("m1",(GateResult("backend:safety","safety",True,("ok",)),),False)
    out=run_counterexample_repair_feedback(CoEvolutionResult(event,"arch-1",(report,),False),lambda *_:pytest.fail("must not repair"))
    assert out.status=="blocked"
