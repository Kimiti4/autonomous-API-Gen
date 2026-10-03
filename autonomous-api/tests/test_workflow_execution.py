from app.engine.workflow_graph import WorkflowScenario
from app.engine.workflow_execution import *

def scenario():
    return WorkflowScenario("swap:retry",("ui","submit","api","svc"),"request-retry")

def runner(s):
    return {"observed_nodes":("ui","submit","api","svc"),
            "passed":True,"evidence":("trace-1","assertion-1")}

def failing_runner(s):
    return {"observed_nodes":("ui","submit","api"),
            "passed":False,"evidence":("trace-fail",),
            "failure_reason":"backend timeout"}

def test_workflow_scenario_can_execute_against_runner():
    e=execute_scenario(scenario(),runner)
    assert e.passed
    assert e.evidence==("trace-1","assertion-1")
    assert execution_is_actionable(e)

def test_failure_becomes_structured_evidence():
    e=execute_scenario(scenario(),failing_runner)
    v=materialize_evidence(e,"ev-1")
    assert v.result=="fail"
    assert v.evidence_id=="ev-1"
    assert execution_is_actionable(e)

def test_missing_evidence_is_not_actionable():
    e=WorkflowExecution("s",("ui",),True,())
    assert not execution_is_actionable(e)

def test_inconclusive_execution_does_not_claim_failure_or_success():
    e=WorkflowExecution("s",("ui",),False,(),None)
    v=materialize_evidence(e,"ev")
    assert v.result=="inconclusive"
