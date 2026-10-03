from app.engine.materialize_coevolution import *
from app.engine.impact_to_coevolution import *
from app.engine.impact_discovery import *
from app.engine.specialized_mutations import frontend_mutation, backend_mutation

def plan():
    impact=discover_impact(
        ImpactRequest("frontend",("frontend.api",),("api-contract",)),
        (ImpactRelation("frontend","backend","api-contract",("trace",)),),
    )
    return build_coevolution_plan(impact,("frontend","backend"),True)

def test_materializes_domain_work():
    p=plan()
    spec=backend_mutation("b1",("backend.api",),"adapt",("e",),lambda x:x)
    w=materialize_coevolution_work(p,(spec,))
    assert w.work[0].domain=="backend"
    assert w.work[0].mutation_id=="b1"
    assert not w.uncertain

def test_missing_domain_mutation_rejected():
    try:
        materialize_coevolution_work(plan(),())
    except ValueError as e:
        assert str(e)=="missing-domain-mutation:backend"
        return
    assert False

def test_incompatible_verification_contract_rejected():
    # Construct a backend plan that requires a property absent from the spec.
    p=CoEvolutionPlan(
        "frontend",
        (DomainPlan("backend","api-contract",("api-contract","custom-property")),),
        ("trace",),True,(),
    )
    spec=backend_mutation("b1",("backend.api",),"adapt",("e",),lambda x:x)
    try:
        materialize_coevolution_work(p,(spec,))
    except ValueError as e:
        assert "mutation-missing-verification-properties:backend:custom-property"==str(e)
        return
    assert False
