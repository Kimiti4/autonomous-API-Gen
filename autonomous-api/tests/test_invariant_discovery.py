from app.engine.invariant_discovery import *

def candidate():
    return discover_candidate(
        "NO-DUP-EFFECT","backend",
        "an operation must not produce duplicate external effects",
        ("cx-1","reg-1"),("trace-1",),"NO-DUP-EFFECT")

def test_candidate_requires_trigger():
    try:
        discover_candidate("x","backend","d",(),("e",),"p")
    except ValueError as e:
        assert str(e)=="invariant-candidate-requires-trigger"
        return
    assert False

def test_candidate_requires_evidence():
    try:
        discover_candidate("x","backend","d",("cx",),(),"p")
    except ValueError as e:
        assert str(e)=="invariant-candidate-requires-evidence"
        return
    assert False

def test_candidate_is_not_invariant_until_validated():
    c=candidate()
    p=promote_candidate(c,("validation-1",))
    assert p.invariant.invariant_id=="NO-DUP-EFFECT"
    assert "validation-1" in p.invariant.evidence

def test_promotion_requires_validation():
    try:
        promote_candidate(candidate(),())
    except ValueError as e:
        assert str(e)=="invariant-promotion-requires-validation"
        return
    assert False
