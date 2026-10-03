from app.engine.evolution_population import *
from app.engine.pareto_architecture import Objective, ArchitectureScore

def m(i,q,l,g=0,p=()):
    return EvolutionMember(ArchitectureLineage(i,p,g,(f"e-{i}",)),ArchitectureScore(i,{"q":q,"l":l},(f"e-{i}",)))

def test_frontier_promotes_multiple_viable_lineages():
    pop=promote_frontier((m("a",10,100),m("b",8,80),m("c",7,120)),
                         (Objective("q","maximize"),Objective("l","minimize")),1)
    assert {x.lineage.architecture_id for x in pop.members}=={"a","b"}

def test_mutation_preserves_parent_lineage():
    child=spawn_mutation(m("a",10,100), "a2",
        ArchitectureScore("a2",{"q":11,"l":100},("e-a2",)),1)
    assert child.lineage.parent_ids==("a",)

def test_crossover_preserves_two_parents():
    child=crossover(m("a",10,100),m("b",8,80),"ab",
        ArchitectureScore("ab",{"q":11,"l":75},("e-ab",)),1)
    assert child.lineage.parent_ids==("a","b")

def test_unevidenced_child_is_rejected():
    try:
        spawn_mutation(m("a",1,1),"a2",ArchitectureScore("a2",{"q":2,"l":1},()),1)
    except ValueError as e:
        assert str(e)=="child-requires-evidence"
        return
    assert False

def test_crossover_requires_distinct_parents():
    a=m("a",1,1)
    try:
        crossover(a,a,"x",ArchitectureScore("x",{"q":2,"l":1},("e",)),1)
    except ValueError as e:
        assert str(e)=="crossover-requires-distinct-parents"
        return
    assert False
