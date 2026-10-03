import pytest
from app.engine.evolution_transaction import execute_evolution_transaction
from app.engine.cross_domain_evolution import CoEvolutionEvent, CoEvolutionResult, DomainChange
from app.engine.evolution_population import ArchitectureLineage, EvolutionMember
from app.engine.fullstack_genome import *
from app.engine.pareto_architecture import ArchitectureScore, Objective
from app.engine.repair_coevolution import RepairCandidate, RepairExecution
from app.engine.verification_plans import GateResult, VerificationReport
from app.engine.specialized_mutations import backend_mutation

def genome():
    return FullStackGenome(
        FrontendGenome("render","state","interaction","a11y","resilience"),
        BackendGenome("service","strong","safe","retry","contract"),
        DataGenome("sql","integrity","expand-contract","strong"),
        SecurityGenome("identity","rbac",("api",),("audit",),"vault"),
        OperationalGenome("containers","metrics","rollback","bounded"),
        "v1","frontend->api->backend")

def source():
    event=CoEvolutionEvent("source-event","parent",(DomainChange("frontend","f1",("state",)),),("impact",))
    report=VerificationReport("f1",(GateResult("frontend:state","state",False,("counterexample",)),),False)
    return CoEvolutionResult(event,"parent",(report,),False)

def member():
    return EvolutionMember(ArchitectureLineage("parent",(),0,("parent",)),ArchitectureScore("parent",{"quality":1.0,"risk":5.0},("parent",)))

def repair_spec():
    return backend_mutation("f1-repair",("frontend.state",),"repair frontend",("state",),lambda g:g)

def dependent_spec():
    return backend_mutation("b1",("backend.api",),"reverify backend",("contract",),lambda g:g)

def test_full_transaction_closes_and_admits_candidate():
    out=execute_evolution_transaction(
        source(),member(),genome(),
        (repair_spec(),),(dependent_spec(),),
        {"frontend":("backend",)},
        {"state":lambda _:True,"contract":lambda _:True},
        {},
        {"state":("repair:evidence",),"contract":("backend:fresh",)},
        (Objective("quality","maximize"),Objective("risk","minimize")),
        {
            "quality":lambda g,c:{"quality":0.93,"_evidence":["measurement:quality"]},
            "risk":lambda g,c:{"risk":0.17,"_evidence":["measurement:risk"]},
        },{},
        event_id="successor-event",
        successor_architecture_id="successor",
        generation=1,
    )
    assert out.successor.passed
    assert out.derived_score.score.values=={"quality":0.93,"risk":0.17}
    assert out.admission.member.lineage.parent_ids==("parent",)

def test_transaction_rejects_missing_measurement_runner():
    with pytest.raises(ValueError,match="missing-measurement-runner:risk"):
        execute_evolution_transaction(
            source(),member(),genome(),
            (repair_spec(),),(dependent_spec(),),
            {"frontend":("backend",)},
            {"state":lambda _:True,"contract":lambda _:True},{},
            {"state":("repair",),"contract":("fresh",)},
            (Objective("quality","maximize"),Objective("risk","minimize")),
            {"quality":lambda g,c:{"quality":1.0,"_evidence":["q"]}},{},
            event_id="event",successor_architecture_id="successor",generation=1)
