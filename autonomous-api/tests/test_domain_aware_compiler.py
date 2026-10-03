from app.engine.synthesis import *
from app.engine.domain_proposals import *
from app.engine.domain_aware_compiler import *

def p(d,change):
    return DomainProposal(d,d,"checkout",d,(change,),(d+"-property",),(d+"-evidence",))

def s():
    return synthesize("s",tuple(
        p(d,d+"-change") for d in ("frontend","backend","data","security","operations")
    ),())

def test_plan_contains_explicit_domain_constraints():
    plan=build_plan(s())
    assert {c.domain for c in plan.constraints}=={"frontend","backend","data","security","operations"}

def test_domain_aware_compilation_requires_real_domain_changes():
    proposal=s()
    genome=compile_domain_aware(proposal)
    assert genome.frontend.framework=="frontend-change"
    assert genome.backend.framework=="backend-change"
    assert genome.security.threat_model=="security-change"

def test_missing_domain_change_is_rejected():
    proposal=s()
    proposal=SynthesizedProposal(
        proposal.proposal_id,proposal.problem_signature,
        proposal.source_proposal_ids,proposal.source_rebuttal_ids,
        proposal.domains,proposal.claim,
        tuple(x for x in proposal.changes if not x.startswith("security-")),
        proposal.target_properties,proposal.evidence,proposal.unresolved_concerns)
    try:
        compile_domain_aware(proposal)
    except ValueError as e:
        assert str(e)=="missing-domain-change:security"
        return
    assert False
