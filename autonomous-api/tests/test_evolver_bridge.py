from app.engine.evolution_domains import *
from app.engine.evolution_selection import *
from app.engine.evolver_bridge import *

def test_verified_multi_domain_option_becomes_evolver_proposal():
    cs=(
        EngineeringCandidate("fe","frontend","sync",("state",),("state",),(),("e-fe",)),
        EngineeringCandidate("be","backend","idempotency",("effect",),("idempotency",),(),("e-be",)),
    )
    assessments=tuple(assess_candidate(c,c.expected_properties,(),c.evidence_basis) for c in cs)
    option=next(o for o in build_options(cs,assessments) if len(o.candidate_ids)==2)
    p=to_evolver_proposal(option,cs)
    assert p.domains==("backend","frontend")
    assert set(p.changes)=={"state","effect"}
    assert proposal_ready_for_evolver(p)

def test_unresolved_risk_blocks_evolver_proposal():
    c=EngineeringCandidate("fe","frontend","sync",("state",),("state",),("unknown-impact",),("e",))
    a=assess_candidate(c,c.expected_properties,(),c.evidence_basis)
    option=build_options((c,),(a,))[0]
    p=to_evolver_proposal(option,(c,))
    assert not proposal_ready_for_evolver(p)

def test_bridge_does_not_authorize_implementation():
    c=EngineeringCandidate("sec","security","authz",("auth",),("authorization",),(),("e",))
    a=assess_candidate(c,c.expected_properties,(),c.evidence_basis)
    p=to_evolver_proposal(build_options((c,),(a,))[0],(c,))
    assert not hasattr(p,"authorize")
    assert not hasattr(p,"implement")
