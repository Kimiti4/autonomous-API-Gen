from app.engine.domain_proposals import *
from app.engine.synthesis import *

def p(i,d):
    return DomainProposal(i,d,"checkout",f"{d} solution",
        (f"{d}-change",),(f"{d}-property",),(f"{d}-evidence",))

def test_synthesis_preserves_lineage_and_evidence():
    a=synthesize("s1",(p("p1","frontend"),p("p2","backend")),())
    assert a.source_proposal_ids==("p1","p2")
    assert a.domains==("backend","frontend")
    assert "frontend-evidence" in a.evidence

def test_rebuttal_concern_blocks_ready_status():
    r=DomainRebuttal("r1","p1","security",("trust-boundary risk",),(),("r-e",))
    a=synthesize("s1",(p("p1","frontend"),), (r,))
    assert not synthesis_ready(a)

def test_synthesis_requires_same_problem():
    x=DomainProposal("p2","backend","payments","x",("c",),("p",),("e",))
    try:
        synthesize("s",(p("p1","frontend"),x),())
    except ValueError as e:
        assert str(e)=="proposal-problem-mismatch"
        return
    assert False

def test_invalid_rebuttal_blocks_synthesis():
    r=DomainRebuttal("r","p1","security",(),(),())
    try:
        synthesize("s",(p("p1","frontend"),),(r,))
    except ValueError as e:
        assert str(e)=="invalid-rebuttal-in-synthesis"
        return
    assert False
