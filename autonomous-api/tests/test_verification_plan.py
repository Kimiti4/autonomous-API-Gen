from app.engine.adversarial_review import CorrectionReview, AdversarialFinding
from app.engine.verification_plan import build_verification_plan, record_verification, is_eligible_for_evolution

def review():
    f=AdversarialFinding("f1","c1","security","high","claim","run security test")
    return CorrectionReview("c1",(f,),("run security test",),"challenged")

def test_review_becomes_traceable_verification_obligation():
    p=build_verification_plan(review())
    assert p.disposition=="requires-evidence"
    assert p.obligations[0].required_evidence==("execution-result","test-output","trace-or-metric")

def test_only_all_passed_obligations_are_evidence_complete():
    p=build_verification_plan(review())
    p=record_verification(p,{"f1:verify":True})
    assert p.disposition=="evidence-complete"
    assert is_eligible_for_evolution(p)

def test_failure_prevents_evolution_eligibility():
    p=build_verification_plan(review())
    p=record_verification(p,{"f1:verify":False})
    assert p.disposition=="failed"
    assert not is_eligible_for_evolution(p)

def test_missing_result_remains_unverified():
    p=build_verification_plan(review())
    p=record_verification(p,{})
    assert p.disposition=="partially-verified"
    assert not is_eligible_for_evolution(p)
