import pytest
from app.engine.successor_admission import materialize_successor_event, admit_successor
from app.engine.cross_domain_evolution import CoEvolutionEvent, CoEvolutionResult, DomainChange
from app.engine.dependency_reexecution import DependencyExecutionResult, DependentDomainExecution
from app.engine.repair_closure import RepairClosure, DependencyInvalidation, SuccessorDomainVerification
from app.engine.repair_coevolution import Counterexample, RepairCandidate, RepairExecution
from app.engine.evolution_population import ArchitectureLineage, EvolutionMember
from app.engine.pareto_architecture import ArchitectureScore, Objective
from app.engine.verification_plans import GateResult, VerificationReport

def member():
    return EvolutionMember(ArchitectureLineage("parent",(),0,("parent",)),ArchitectureScore("parent",{"quality":1.0,"risk":5.0},("parent",)))

def result():
    event=CoEvolutionEvent("old-event","parent",(DomainChange("frontend","f1",("state",)),),("impact",))
    report=VerificationReport("f1",(GateResult("frontend:state","state",False,("cx",)),),False)
    return CoEvolutionResult(event,"old",(report,),False)

def closure():
    repair=RepairExecution(
        RepairCandidate("f1","f1-repair","frontend","repair",("state",)),
        None,
        VerificationReport("f1-repair",(GateResult("frontend:state","state",True,("repair",)),),True))
    return RepairClosure("old-event","parent",(Counterexample("f1","frontend",("state",),("cx",)),),
        DependencyInvalidation("frontend",("frontend","backend"),("cx",)),(repair,),(), "child",True,())

def dep():
    report=VerificationReport("backend",(GateResult("backend:contract","contract",True,("fresh",)),),True)
    ex=DependentDomainExecution("backend","b1",None,report)
    return DependencyExecutionResult((ex,),None,closure())

def test_successor_event_contains_fresh_evidence_and_parent_link():
    score=ArchitectureScore("child",{"quality":1.2,"risk":4.0},("score:evidence",))
    successor=materialize_successor_event(result(),dep(),event_id="successor-event",source_member=member(),score=score)
    assert successor.parent_event_id=="old-event"
    assert successor.architecture_id=="child"
    assert successor.passed
    assert "fresh" in successor.evidence
    assert "score:evidence" in successor.evidence

def test_admission_requires_passing_successor():
    score=ArchitectureScore("child",{"quality":1.2,"risk":4.0},("score",))
    successor=materialize_successor_event(result(),dep(),event_id="successor-event",source_member=member(),score=score)
    admitted=admit_successor(member(),successor,score,(Objective("quality","maximize"),Objective("risk","minimize")),1)
    assert admitted.member.lineage.parent_ids==("parent",)
    assert admitted.population.generation==1

def test_failed_successor_cannot_enter_population():
    score=ArchitectureScore("child",{"quality":1.2,"risk":4.0},("score",))
    successor=materialize_successor_event(result(),dep(),event_id="successor-event",source_member=member(),score=score)
    bad=successor.__class__(successor.event,successor.architecture_id,successor.parent_event_id,successor.evidence,successor.reports,False)
    with pytest.raises(ValueError,match="successor-verification-failed"):
        admit_successor(member(),bad,score,(Objective("quality","maximize"),),1)
