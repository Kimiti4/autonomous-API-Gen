from app.engine.architectural_memory import *
from app.engine.domain_council import *

def memory(i,domain,outcome):
    return record_memory(
        i,"checkout","repair",
        (domain,),("change",),outcome,
        ("property",),(f"e-{i}",))

def test_domain_review_surfaces_failed_prior_work():
    idx=index_memory(MemoryIndex(),memory("m1","backend","failure"))
    r=review_domain("backend","checkout",idx)
    assert r.memory_ids==("m1",)
    assert "m1:previous-failure" in r.concerns
    assert r.supporting_evidence==("e-m1",)

def test_successful_memory_can_inform_domain_review():
    idx=index_memory(MemoryIndex(),memory("m1","frontend","success"))
    r=review_domain("frontend","checkout",idx)
    assert r.memory_ids==("m1",)
    assert r.concerns==()

def test_cross_domain_review_shares_relevant_memory():
    idx=index_memory(MemoryIndex(),memory("b","backend","failure"))
    idx=index_memory(idx,memory("s","security","success"))
    r=review_across_domains("checkout",("frontend","backend","security"),idx)
    assert r.shared_memory_ids==("b","s")
    assert len(r.reviews)==3
