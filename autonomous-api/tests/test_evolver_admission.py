from app.engine.evolver_bridge import *
from app.engine.evolver_admission import *

def proposal():
    c=EngineeringCandidate(
        "fe","frontend","sync",("state",),("state",),(),("trace",)
    )
    a=assess_candidate(c,c.expected_properties,(),c.evidence_basis)
    return to_evolver_proposal(build_options((c,),(a,))[0],(c,))

def test_ready_proposal_crosses_real_admission_boundary():
    a=admit_proposal(proposal(),required_domains=("frontend",),required_properties=("state",))
    assert a.admitted
    context=admission_to_evolution_context(a)
    assert context["proposal_id"]=="fe"
    assert context["candidate_ids"]==("fe",)

def test_missing_required_domain_is_rejected():
    a=admit_proposal(proposal(),required_domains=("backend",))
    assert not a.admitted
    assert "missing-domains:backend" in a.reasons

def test_missing_required_property_is_rejected():
    a=admit_proposal(proposal(),required_properties=("authorization",))
    assert not a.admitted
    assert "missing-properties:authorization" in a.reasons

def test_rejected_proposal_cannot_create_evolution_context():
    a=admit_proposal(proposal(),required_domains=("security",))
    assert not a.admitted
    try:
        admission_to_evolution_context(a)
    except ValueError:
        return
    assert False, "rejected proposal created an evolution context"
