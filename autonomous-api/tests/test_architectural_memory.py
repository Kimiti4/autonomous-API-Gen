from app.engine.architectural_memory import *

def m(i="m1"):
    return record_memory(i,"duplicate-effect","idempotency repair",
        ("backend","security"),("idempotency","authz"),"success",
        ("NO-DUPLICATE-EFFECT",),("trace-1",))

def test_memory_requires_evidence():
    try:
        record_memory("m","p","h",("backend",),("x",),"success",("p",),())
    except ValueError as e:
        assert str(e)=="architectural-memory-requires-evidence"
        return
    assert False

def test_memory_is_indexed_and_retrievable():
    idx=index_memory(MemoryIndex(),m())
    found=retrieve_memory(idx,MemoryQuery("duplicate-effect",("backend",)))
    assert found[0].memory_id=="m1"

def test_unrelated_domain_does_not_match_when_domain_filter_given():
    idx=index_memory(MemoryIndex(),m())
    assert retrieve_memory(idx,MemoryQuery("duplicate-effect",("frontend",)))==()

def test_duplicate_memory_ids_are_rejected():
    idx=index_memory(MemoryIndex(),m())
    try:
        index_memory(idx,m())
    except ValueError as e:
        assert str(e)=="duplicate-memory-id"
        return
    assert False

def test_confidence_promotion_requires_new_evidence():
    x=m()
    try:
        promote_confidence(x,(),"high")
    except ValueError as e:
        assert str(e)=="promotion-requires-new-evidence"
        return
    assert False

def test_confidence_promotion_adds_evidence():
    x=promote_confidence(m(),("trace-2",),"high")
    assert x.confidence=="high"
    assert set(x.evidence)=={"trace-1","trace-2"}
