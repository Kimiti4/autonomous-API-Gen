from app.engine.fullstack_genome import *
from app.engine.fullstack_population import *

def g():
    return FullStackGenome(
        FrontendGenome("adaptive","state","events","semantic","retry"),
        BackendGenome("modular","transactional","controlled","isolated","versioned"),
        DataGenome("relational","constraints","expand-contract","transactional"),
        SecurityGenome("session","object",("api",),("validation",),"vault"),
        OperationalGenome("immutable","metrics","atomic","bounded"),
        "versioned","explicit",
    )

def test_population_accepts_valid_fullstack_offspring():
    p=PopulationGeneration(0,(GenomeIndividual("p1",g()),))
    child=GenomeIndividual("c1",g(),("p1",))
    n=next_generation(p,(child,))
    assert n.generation==1
    assert [x.individual_id for x in n.individuals]==["c1"]

def test_invalid_offspring_is_rejected():
    x=g()
    broken=FullStackGenome(x.frontend,x.backend,x.data,
        SecurityGenome("session","object",(),("validation",),"vault"),
        x.operations,x.api_contract,x.state_flow)
    p=PopulationGeneration(0,())
    n=next_generation(p,(GenomeIndividual("bad",broken),))
    assert n.individuals==()

def test_crossover_records_both_parents():
    a=GenomeIndividual("a",g())
    b=GenomeIndividual("b",g())
    c=crossover_individuals(a,b,"child")
    assert c.parent_ids==("a","b")

def test_mutation_records_parent():
    a=GenomeIndividual("a",g())
    c=mutate_individual(a,"child",lambda x:x)
    assert c.parent_ids==("a",)
