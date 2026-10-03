from app.engine.specialized_mutations import *
from app.engine.fullstack_genome import *

def g():
    return FullStackGenome(
        FrontendGenome("f","b","c","d","e"),
        BackendGenome("a","b","c","d","e"),
        DataGenome("a","b","c","d"),
        SecurityGenome("a","b",("t",),("c",),"d"),
        OperationalGenome("a","b","c","d"),"p","c")

def test_frontend_operator_has_senior_quality_verification():
    s=frontend_mutation("f1",("frontend.framework",),"improve",("e",),lambda x:x)
    assert "accessibility" in s.verification_properties
    assert s.risk_class=="medium"

def test_backend_operator_requires_effect_safety():
    s=backend_mutation("b1",("backend.framework",),"improve",("e",),lambda x:x)
    assert "effect-safety" in s.verification_properties

def test_security_is_critical():
    s=security_mutation("s1",("security.threat_model",),"improve",("e",),lambda x:x)
    assert s.risk_class=="critical"
    assert "trust-boundary" in s.verification_properties

def test_fullstack_requires_end_to_end_verification():
    s=fullstack_mutation("x1",("frontend.framework","backend.framework"),
                         "contract",("e",),lambda x:x)
    assert "end-to-end-flow" in s.verification_properties
