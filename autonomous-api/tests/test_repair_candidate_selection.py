from app.engine.repository_root_cause import RepairCandidate
from app.engine.repair_candidate_selection import CandidateEvaluation, select_verified_repair

def c(i): return RepairCandidate(i,"h","strategy","r",("a.py",),("a.py",),.5)

def test_selects_only_verified_regression_free_candidate():
    r=select_verified_repair(
        (c("a"),c("b")),
        (CandidateEvaluation("a",True,.8,True,.5,("e",)),
         CandidateEvaluation("b",True,.9,False,.9,("e",))))
    assert r.selected_candidate_id=="a"

def test_no_verified_candidate_means_no_admission():
    r=select_verified_repair(
        (c("a"),),
        (CandidateEvaluation("a",True,.9,False,.9,("e",)),))
    assert r.selected_candidate_id is None

def test_missing_evaluation_fails_closed():
    r=select_verified_repair((c("a"),),())
    assert r.selected_candidate_id is None
    assert "missing-candidate-evaluation" in r.evaluations[0].rejection_reasons
