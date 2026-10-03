from app.engine.domain_mutation import *
from app.engine.fullstack_genome import *

def g():
    return FullStackGenome(
        FrontendGenome("f","b","c","d","e"),
        BackendGenome("a","b","c","d","e"),
        DataGenome("a","b","c","d"),
        SecurityGenome("a","b",("t",),("c",),"d"),
        OperationalGenome("a","b","c","d"),"p","c")

def test_frontend_mutation_is_scoped():
    r=MutationRequest("frontend",("frontend.framework",),"improve",("e",))
    validate_mutation_request(r)

def test_cross_domain_mutation_requires_fullstack_domain():
    r=MutationRequest("frontend",("backend.framework",),"bad",("e",))
    try:
        validate_mutation_request(r)
    except ValueError as e:
        assert str(e)=="mutation-crosses-domain-boundary"
        return
    assert False

def test_mutation_requires_evidence():
    r=MutationRequest("security",("security.threat_model",),"improve",())
    try:
        validate_mutation_request(r)
    except ValueError as e:
        assert str(e)=="mutation-requires-evidence"
        return
    assert False

def test_fullstack_mutation_can_span_domains():
    r=MutationRequest("fullstack",("frontend.framework","backend.framework"),"contract",("e",))
    validate_mutation_request(r)

def test_unknown_domain_rejected():
    r=MutationRequest("ml",("frontend.framework",),"x",("e",))
    try:
        validate_mutation_request(r)
    except ValueError as e:
        assert str(e)=="unknown-mutation-domain"
        return
    assert False
