from app.engine.counterexample_guidance import *
from app.engine.fullstack_genome import *

def g():
    return FullStackGenome(
        FrontendGenome("a","b","c","d","e"),
        BackendGenome("a","b","c","d","e"),
        DataGenome("a","b","c","d"),
        SecurityGenome("a","b",("t",),("c",),"d"),
        OperationalGenome("a","b","c","d"),"contract","flow")

def test_counterexample_becomes_targeted_hypothesis():
    c=Counterexample("cx1","backend","INV-NO-DUPLICATE-EFFECT",("trace",),{})
    h=infer_mutation_hypothesis(c)
    assert h.domain=="backend"
    assert h.target_properties==("INV-NO-DUPLICATE-EFFECT",)

def test_guided_mutation_preserves_lineage():
    c=Counterexample("cx1","backend","INV-NO-DUPLICATE-EFFECT",("trace",),{})
    h=infer_mutation_hypothesis(c)
    m=apply_guided_mutation("parent",g(),h,lambda x:x)
    assert m.parent_id=="parent"
    assert m.hypothesis.counterexample_id=="cx1"

def test_unresolved_counterexample_is_not_accepted():
    c=Counterexample("cx1","security","AUTHZ",("trace",),{})
    try:
        require_resolution_evidence(c,{"resolved_properties":[],"evidence":["new"]})
    except ValueError as e:
        assert str(e)=="counterexample-not-resolved"
        return
    assert False

def test_resolution_requires_new_evidence():
    c=Counterexample("cx1","security","AUTHZ",("old",),{})
    try:
        require_resolution_evidence(c,{"resolved_properties":["AUTHZ"],"evidence":[]})
    except ValueError as e:
        assert str(e)=="resolution-requires-evidence"
        return
    assert False

def test_resolved_counterexample_returns_evidence():
    c=Counterexample("cx1","security","AUTHZ",("old",),{})
    assert require_resolution_evidence(c,{"resolved_properties":["AUTHZ"],"evidence":["new"]})==("new",)
