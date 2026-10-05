import pytest
from app.engine.truth_gate import EvidenceClaim,EpistemicStatus,evaluate_claim

def test_verified_claim_requires_real_attributable_evidence():
 c=EvidenceClaim("C-1","cand-1",EpistemicStatus.VERIFIED,("E-1",),"verification-run-1")
 assert evaluate_claim(c,{"E-1":{"passed":True}},expected_subject_id="cand-1").admissible
def test_missing_evidence_is_not_invented():
 c=EvidenceClaim("C-1","cand-1",EpistemicStatus.VERIFIED,("E-404",),"run")
 r=evaluate_claim(c,{},expected_subject_id="cand-1")
 assert not r.admissible and "missing-evidence:E-404" in r.reasons
def test_unknown_stays_unknown():
 c=EvidenceClaim("C-1","cand-1",EpistemicStatus.UNKNOWN,(),"run")
 r=evaluate_claim(c,{})
 assert not r.admissible and r.status is EpistemicStatus.UNKNOWN
def test_subject_mismatch_fails_closed():
 c=EvidenceClaim("C-1","cand-1",EpistemicStatus.VERIFIED,("E-1",),"run")
 assert not evaluate_claim(c,{"E-1":{}},expected_subject_id="cand-2").admissible
