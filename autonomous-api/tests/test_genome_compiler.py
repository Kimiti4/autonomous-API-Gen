from app.engine.synthesis import *
from app.engine.domain_proposals import *
from app.engine.genome_compiler import *

def proposal():
    p1=DomainProposal("p1","frontend","checkout","frontend",
        ("frontend-contracts",),("A11Y",),("f1",))
    p2=DomainProposal("p2","backend","checkout","backend",
        ("backend-idempotency",),("IDEMPOTENCY",),("b1",))
    return synthesize("s1",(p1,p2),())

def test_ready_synthesis_compiles_to_genome():
    c=compile_synthesis(proposal())
    assert c.proposal_id=="s1"
    assert c.source_proposal_ids==("p1","p2")
    assert c.genome.frontend is not None
    assert c.genome.backend is not None

def test_unresolved_synthesis_cannot_compile():
    p=DomainProposal("p1","security","checkout","security",
        ("security-authz",),("AUTHZ",),("s1",))
    r=DomainRebuttal("r1","p1","backend",("risk",),(),("r1e",))
    s=synthesize("s",(p,),(r,))
    try:
        compile_synthesis(s)
    except ValueError as e:
        assert str(e)=="synthesis-not-ready"
        return
    assert False
