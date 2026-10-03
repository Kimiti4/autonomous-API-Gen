from app.engine.fullstack_fitness import *
from app.engine.fullstack_genome import *
from app.engine.fullstack_population import *

def ind(i):
    g=FullStackGenome(
        FrontendGenome("a","b","c","d","e"),
        BackendGenome("a","b","c","d","e"),
        DataGenome("a","b","c","d"),
        SecurityGenome("a","b",("t",),("c",),"d"),
        OperationalGenome("a","b","c","d"),"c","s")
    return GenomeIndividual(i,g)

def test_dominance_requires_no_worse_objective_and_one_better():
    assert dominates(Fitness(1,.9,.8,.8,.8,.8),Fitness(.9,.9,.8,.8,.8,.8))
    assert not dominates(Fitness(.9,.9,.8,.8,.8,.8),Fitness(1,.9,.8,.8,.8,.8))

def test_tradeoff_candidates_can_both_survive_pareto_selection():
    a=EvaluatedIndividual(ind("a"),Fitness(1,.6,.9,.8,.9,.8),("a",))
    b=EvaluatedIndividual(ind("b"),Fitness(.9,1,.7,.9,.8,.9),("b",))
    front=pareto_front((a,b))
    assert {x.individual.individual_id for x in front}=={"a","b"}

def test_dominated_candidate_is_removed():
    a=EvaluatedIndividual(ind("a"),Fitness(1,1,1,1,1,1),("a",))
    b=EvaluatedIndividual(ind("b"),Fitness(.8,.8,.8,.8,.8,.8),("b",))
    assert [x.individual.individual_id for x in pareto_front((a,b))]==["a"]

def test_invalid_fitness_range_is_rejected():
    assert not fitness_is_valid(Fitness(1.1,0,0,0,0,0))
