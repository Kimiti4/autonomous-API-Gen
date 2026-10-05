from app.engine.repository_root_cause import RepairCandidate
from app.engine.repair_candidate_selection import CandidateEvaluation
from app.engine.comparable_repair_selection import select_comparable_repair

def c(i): return RepairCandidate(i,"H","strategy","reason",("x",),("x",),.5)
def e(i,v=1.0,m=1.0): return CandidateEvaluation(i,True,v,True,m,("E-"+i,))
def test_selects_only_comparable_evidenced_candidates():
 r=select_comparable_repair((c("A"),c("B")),(e("A",2,1),e("B",1,2)))
 assert r.selection.selected_candidate_id=="A"
 assert r.optimality_status=="ranked-with-comparable-evidence"
def test_incomplete_candidate_is_not_called_optimal():
 r=select_comparable_repair((c("A"),c("B")),(e("A",2,1),))
 assert r.selection.selected_candidate_id=="A"
 assert r.compared_candidate_ids==("A",)
 assert r.optimality_status=="ranked-with-comparable-evidence"
def test_no_evidence_is_unknown():
 r=select_comparable_repair((c("A"),),(CandidateEvaluation("A",True,2,True,1,()),))
 assert r.selection.selected_candidate_id is None
 assert r.optimality_status=="unknown-no-comparable-candidate"
