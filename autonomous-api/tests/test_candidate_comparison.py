from app.engine.candidate_comparison import *

def assessment():
    return CandidateAssessment("c1",tuple(
        DimensionEvidence(d,"supported",("e-"+d,)) for d in DIMENSIONS
    ))

def test_all_engineering_dimensions_are_explicit():
    a=assessment()
    assert validate_assessment(a)==()
    assert set(e.dimension for e in a.evidence)==set(DIMENSIONS)

def test_unverified_and_bounded_dimensions_remain_visible():
    a=CandidateAssessment("c1",(
        DimensionEvidence("correctness","supported"),
        DimensionEvidence("performance","bounded"),
    ))
    assert unresolved_dimensions(a)==("performance",)
    assert can_be_governed_for_evolution(a)

def test_contradicted_candidate_cannot_be_governed():
    a=CandidateAssessment("c1",(
        DimensionEvidence("security","contradicted",("e1",)),
    ))
    assert not can_be_governed_for_evolution(a)

def test_comparison_does_not_create_a_single_score():
    a=assessment()
    c=compare_candidates((a,))
    assert c.dimensions==DIMENSIONS
    assert not hasattr(c,"score")
