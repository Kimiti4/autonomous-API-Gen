from app.engine.cross_domain_evolution import *
from app.engine.evolution_population import *
from app.engine.pareto_architecture import ArchitectureScore
from app.engine.specialized_mutations import frontend_mutation, backend_mutation
from app.engine.verification_plans import VerificationReport, GateResult

def source():
    return EvolutionMember(
        ArchitectureLineage("a",(),0,("e",)),
        ArchitectureScore("a",{"q":8},("e",)))

def specs():
    return (
        frontend_mutation("f1",("frontend.api",),"contract",("e",),lambda x:x),
        backend_mutation("b1",("backend.api",),"contract",("e",),lambda x:x),
    )

def test_cross_domain_event_requires_distinct_domains():
    e=create_coevolution_event("x",source(),specs(),("integration-trace",))
    assert {c.domain for c in e.changes}=={"frontend","backend"}

def test_duplicate_domain_rejected():
    s=frontend_mutation("f1",("x",),"r",("e",),lambda x:x)
    s2=frontend_mutation("f2",("y",),"r",("e",),lambda x:x)
    try:
        create_coevolution_event("x",source(),(s,s2),("e",))
    except ValueError as e:
        assert str(e)=="coevolution-duplicate-domain"
        return
    assert False

def test_all_domain_verifications_required():
    e=create_coevolution_event("x",source(),specs(),("e",))
    r=(VerificationReport("f1",(),True),)
    try:
        complete_coevolution(e,"child",r)
    except ValueError as e:
        assert "missing-domain-verification:b1"==str(e)
        return
    assert False

def test_cross_domain_event_passes_only_if_all_pass():
    e=create_coevolution_event("x",source(),specs(),("e",))
    r=(
        VerificationReport("f1",(),True),
        VerificationReport("b1",(),True),
    )
    result=complete_coevolution(e,"child",r)
    assert result.passed
