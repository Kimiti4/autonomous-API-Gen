from app.engine.domain_proposals import *

def p():
    return DomainProposal("p1","security","checkout","strengthen authz",
        ("object-level-policy",),("AUTHZ",),("sec-1",))

def test_valid_proposal_enters_evaluation():
    a=validate_proposal(p())
    assert a.accepted_for_evaluation

def test_proposal_without_evidence_is_rejected():
    x=DomainProposal("p1","security","checkout","claim",("x",),("p",),())
    a=validate_proposal(x)
    assert not a.accepted_for_evaluation
    assert "proposal-requires-evidence" in a.reasons

def test_rebuttal_requires_evidence_and_concern():
    r=DomainRebuttal("r1","p1","backend",("consistency risk",),(),("e",))
    assert validate_rebuttal(r)==()

def test_empty_rebuttal_is_rejected():
    r=DomainRebuttal("r1","p1","backend",(),(),())
    assert validate_rebuttal(r)

def test_proposal_can_be_recorded_as_bounded_memory():
    idx=record_domain_proposal(MemoryIndex(),p())
    assert idx.memories[0].memory_id=="p1"
    assert idx.memories[0].outcome=="bounded"
