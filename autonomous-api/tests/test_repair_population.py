from app.engine.repair_population import *
from app.engine.verification_to_repair import *
from app.engine.verification_plans import GateResult, VerificationReport
from app.engine.evolution_population import *
from app.engine.pareto_architecture import Objective, ArchitectureScore

def source():
    return EvolutionMember(
        ArchitectureLineage("a",(),0,("e-a",)),
        ArchitectureScore("a",{"quality":8,"latency":100},("e-a",)))

def candidate():
    r=VerificationReport("a",(GateResult("backend:effect-safety","effect-safety",False,("trace",)),),False)
    return create_repair_candidate(r,r.results[0])

def test_repair_enters_new_generation():
    p=promote_repair(source(),candidate(),"a-repair",
        ArchitectureScore("a-repair",{"quality":9,"latency":90},("repair-e",)),1)
    assert p.member.lineage.parent_ids==("a",)
    assert p.lineage.source_architecture_id=="a"
    assert p.lineage.failed_gate_id=="backend:effect-safety"

def test_repair_requires_evidence():
    try:
        promote_repair(source(),candidate(),"a-repair",
            ArchitectureScore("a-repair",{"quality":9,"latency":90},()),1)
    except ValueError as e:
        assert str(e)=="repair-score-requires-evidence"
        return
    assert False

def test_repair_can_replace_dominated_parent():
    repaired=promote_repair(source(),candidate(),"a-repair",
        ArchitectureScore("a-repair",{"quality":9,"latency":90},("e-r",)),1).member
    out=reintegrate_population(
        (source(),),
        repaired,
        (Objective("quality","maximize"),Objective("latency","minimize")))
    assert [m.lineage.architecture_id for m in out]==["a-repair"]

def test_repair_can_coexist_when_tradeoff_is_non_dominated():
    repaired=promote_repair(source(),candidate(),"a-repair",
        ArchitectureScore("a-repair",{"quality":7,"latency":70},("e-r",)),1).member
    out=reintegrate_population(
        (source(),),
        repaired,
        (Objective("quality","maximize"),Objective("latency","minimize")))
    assert {m.lineage.architecture_id for m in out}=={"a","a-repair"}
