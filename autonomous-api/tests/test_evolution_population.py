from app.engine.evolution_population import *
from app.engine.pareto_architecture import ArchitectureScore, Objective

def s(i,q,l,e=("e",)):
    return ArchitectureScore(i,{"quality":q,"latency":l},e)

def test_seed_population_creates_generation_zero_lineages():
    p=seed_population((s("a",10,100),s("b",8,80)))
    assert p.generation==0
    assert p.members[0].lineage.parent_ids==()

def test_frontier_selection_deactivates_dominated_members():
    p=seed_population((s("a",10,100),s("b",8,80),s("c",7,120)))
    p=select_frontier(p,(Objective("quality","maximize"),Objective("latency","minimize")))
    active={m.score.architecture_id for m in p.members if m.active}
    assert active=={"a","b"}

def test_crossover_preserves_two_parent_lineage():
    p=seed_population((s("a",10,100),s("b",8,80)))
    child=crossover(p.members[0],p.members[1],"c",s("c",9,90))
    assert child.lineage.parent_ids==("a","b")
    assert child.lineage.generation==1

def test_crossover_requires_evidence():
    p=seed_population((s("a",1,1),s("b",2,2)))
    try:
        crossover(p.members[0],p.members[1],"c",s("c",2,1,()))
    except ValueError as e:
        assert str(e)=="offspring-requires-evidence"
        return
    assert False

def test_offspring_generation_must_increase():
    p=seed_population((s("a",1,1),))
    child=PopulationMember(s("b",2,2),Lineage("b",("a",),0,("e",)))
    try:
        add_offspring(p,(child,))
    except ValueError as e:
        assert str(e)=="offspring-generation-must-increase"
        return
    assert False
