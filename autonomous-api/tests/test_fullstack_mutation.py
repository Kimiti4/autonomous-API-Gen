from app.engine.fullstack_genome import *
from app.engine.fullstack_mutation import *

def g():
    return FullStackGenome(
        FrontendGenome("adaptive","state-machine","events","semantic","retry"),
        BackendGenome("modular","transactional","controlled","isolated","versioned"),
        DataGenome("relational","constraints","expand-contract","transactional"),
        SecurityGenome("session","object-level",("api",),("validation",),"vault"),
        OperationalGenome("immutable","metrics","atomic","bounded"),
        "versioned-contract","explicit-flow",
    )

def test_frontend_mutation_preserves_other_domains():
    x=safe_mutation(g(),"frontend",{"state_model":"event-sourced"})
    assert x.frontend.state_model=="event-sourced"
    assert x.backend==g().backend
    assert x.security==g().security

def test_recombination_preserves_cross_layer_contracts():
    a=g()
    b=mutate_backend(g(),service_model="actor")
    x=recombine(a,b)
    assert x.backend.service_model=="actor"
    assert x.api_contract==a.api_contract
    assert x.state_flow==a.state_flow

def test_security_mutation_cannot_remove_required_trust_boundary():
    try:
        safe_mutation(g(),"security",{"trust_boundaries":()})
    except ValueError as e:
        assert "authorization-requires-trust-boundaries" in str(e)
        return
    assert False

def test_frontend_state_mutation_cannot_remove_state_flow():
    try:
        safe_mutation(g(),"frontend",{"state_model":"complex"})
    except Exception:
        assert False
    try:
        broken=FullStackGenome(g().frontend,g().backend,g().data,g().security,g().operations,g().api_contract,"")
        assert compatibility_errors(broken)
    except Exception:
        assert False

def test_unknown_domain_is_rejected():
    try:
        safe_mutation(g(),"mobile",{})
    except ValueError as e:
        assert str(e)=="unknown-domain:mobile"
        return
    assert False
