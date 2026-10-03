import pytest
from app.engine.candidate_measurements import execute_candidate_measurements, measurement_evidence_map
from app.engine.fullstack_genome import *

def genome():
    return FullStackGenome(
        FrontendGenome("render","state","interaction","a11y","resilience"),
        BackendGenome("service","strong","safe","retry","contract"),
        DataGenome("sql","integrity","expand-contract","strong"),
        SecurityGenome("identity","rbac",("api",),("audit",),"vault"),
        OperationalGenome("containers","metrics","rollback","bounded"),
        "v1","frontend->api->backend")

def test_candidate_measurements_are_observed_from_runner():
    result=execute_candidate_measurements(
        "child",genome(),
        (Objective("quality","maximize"),Objective("risk","minimize")),
        {
            "quality":lambda g,c: {"quality":0.93,"_evidence":["run:quality"]},
            "risk":lambda g,c: {"risk":0.17,"_evidence":["run:risk"]},
        },{})
    assert measurement_evidence_map(result)=={
        "quality":(0.93,("run:quality",)),
        "risk":(0.17,("run:risk",))}
    assert result.architecture_id=="child"

def test_missing_runner_fails_closed():
    with pytest.raises(ValueError,match="missing-measurement-runner:risk"):
        execute_candidate_measurements(
            "child",genome(),
            (Objective("quality","maximize"),Objective("risk","minimize")),
            {"quality":lambda g,c: {"quality":1.0,"_evidence":["q"]}},{})

def test_unobserved_metric_cannot_become_score_input():
    with pytest.raises(ValueError,match="measurement-runner-missing-evidence:quality"):
        execute_candidate_measurements(
            "child",genome(),(Objective("quality","maximize"),),
            {"quality":lambda g,c: {"quality":1.0}},{})
