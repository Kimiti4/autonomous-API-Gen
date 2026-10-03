import pytest
from app.engine.evidence_scoring import derive_architecture_score
from app.engine.dependency_reexecution import DependencyExecutionResult, DependentDomainExecution
from app.engine.repair_coevolution import RepairCandidate, RepairExecution
from app.engine.repair_closure import RepairClosure, DependencyInvalidation
from app.engine.verification_plans import GateResult, VerificationReport
from app.engine.pareto_architecture import Objective

def report(mid="r"):
    return VerificationReport(mid,(GateResult("g","property",True,("verified",)),),True)

def deps():
    return DependencyExecutionResult(
        (DependentDomainExecution("backend","b1",None,report("b1")),),
        None,
        None,
    )

def test_score_is_derived_from_verified_measurements():
    repairs=(RepairExecution(
        RepairCandidate("f","fr","frontend","repair",("property",)),
        None,report("fr")),)
    out=derive_architecture_score(
        "child",repairs,deps(),
        (Objective("quality","maximize"),Objective("risk","minimize")),
        measurement_evidence={
            "quality":(0.91,("metric:quality",)),
            "risk":(0.18,("metric:risk",)),
        },
    )
    assert out.score.values=={"quality":0.91,"risk":0.18}
    assert "verified" in out.score.evidence
    assert "metric:quality" in out.score.evidence

def test_failed_verification_cannot_produce_score():
    bad=VerificationReport("bad",(GateResult("g","property",False,("counterexample",)),),False)
    repairs=(RepairExecution(
        RepairCandidate("f","fr","frontend","repair",("property",)),
        None,bad),)
    with pytest.raises(ValueError,match="score-requires-passing-verification"):
        derive_architecture_score("child",repairs,deps(),(Objective("quality","maximize"),),measurement_evidence={"quality":(1.0,("metric",))})

def test_missing_or_unsubstantiated_measurement_is_rejected():
    repairs=(RepairExecution(RepairCandidate("f","fr","frontend","repair",("property",)),None,report("fr")),)
    with pytest.raises(ValueError,match="missing-measurement:quality"):
        derive_architecture_score("child",repairs,deps(),(Objective("quality","maximize"),),measurement_evidence={})
