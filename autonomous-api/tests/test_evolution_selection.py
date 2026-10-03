from app.engine.evolution_domains import *
from app.engine.evolution_selection import *

def candidates():
    return (
        EngineeringCandidate("fe","frontend","sync",("state",),("state",),(),("e-fe",)),
        EngineeringCandidate("be","backend","idempotency",("effect",),("idempotency",),(),("e-be",)),
        EngineeringCandidate("sec","security","authz",("auth",),("authorization",),(),("e-sec",)),
    )

def test_candidate_assessment_requires_evidence_and_no_failed_properties():
    c=candidates()[0]
    assert assess_candidate(c,("state",),(),("e",)).viable
    assert not assess_candidate(c,("state",),("bad",),("e",)).viable
    assert not assess_candidate(c,("state",),(),()).viable

def test_multi_domain_composition_is_available():
    cs=candidates()
    assessments=tuple(assess_candidate(c,c.expected_properties,(),c.evidence_basis) for c in cs)
    options=build_options(cs,assessments)
    composed=next(o for o in options if len(o.candidate_ids)==3)
    assert set(composed.domains)=={"frontend","backend","security"}
    assert composed.eligible_for_governance

def test_overlapping_changes_create_a_conflict_flag():
    a=EngineeringCandidate("a","frontend","a",("state",),(),(),("e",))
    b=EngineeringCandidate("b","backend","b",("state",),(),(),("e",))
    comp=compose_candidates((a,b))
    assert comp.conflicts==("overlapping-change:a:b",)

def test_unverified_candidate_cannot_enter_composed_governance_option():
    cs=candidates()
    assessments=(
        assess_candidate(cs[0],("state",),(),("e",)),
        assess_candidate(cs[1],(),("bad",),("e",)),
        assess_candidate(cs[2],("authorization",),(),("e",)),
    )
    options=build_options(cs,assessments)
    assert not any(len(o.candidate_ids)==3 for o in options)
