from app.engine.correction_synthesis import CorrectionCandidate
from app.engine.adversarial_review import review_correction, review_candidates

def candidate(strategy):
    return CorrectionCandidate("s:"+strategy,strategy,(),("invariant",),(),())

def test_guard_correction_is_adversarially_challenged():
    r=review_correction(candidate("strengthen-transition-guards"))
    assert r.disposition=="challenged"
    assert any(f.category=="reliability" for f in r.findings)

def test_serialization_is_checked_for_deadlock_and_performance():
    r=review_correction(candidate("serialize-conflicting-effects"))
    assert any(f.category=="performance" for f in r.findings)
    assert any(f.category=="reliability" and f.severity=="high" for f in r.findings)

def test_compensation_is_checked_for_duplicate_effects():
    r=review_correction(candidate("add-compensation-or-recovery"))
    assert any(f.category=="correctness" and f.severity=="high" for f in r.findings)

def test_all_candidates_are_reviewed():
    rs=review_candidates((candidate("strengthen-transition-guards"),
                          candidate("serialize-conflicting-effects")))
    assert len(rs)==2
    assert all(r.obligations for r in rs)
