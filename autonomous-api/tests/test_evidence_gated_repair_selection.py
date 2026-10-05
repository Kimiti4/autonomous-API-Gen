from app.engine.repair_candidate_selection import CandidateEvaluation
from app.engine.evidence_gated_repair_selection import select_evidence_gated_repair

def c(cid,evidence=("E",),passed=True,reg=True):
 return type("C",(),{"candidate_id":cid})(), CandidateEvaluation(cid,passed,1.0,reg,1.0,evidence)

def test_missing_evidence_cannot_win():
 c1,e1=c("a",evidence=())
 c2,e2=c("b")
 d=select_evidence_gated_repair((c1,c2),(e1,e2))
 assert d.selection.selected_candidate_id=="b"
 assert d.epistemic_status=="verified-candidate-selected"

def test_no_evidenced_candidate_is_unknown_not_fixed():
 c1,e1=c("a",evidence=(),passed=True)
 d=select_evidence_gated_repair((c1,),(e1,))
 assert d.selection.selected_candidate_id is None
 assert d.epistemic_status=="unknown-no-evidenced-repair-admitted"
 assert not d.evidence_complete
