import pytest
from app.engine.repair_candidate_selection import CandidateEvaluation
from app.engine.repair_candidate_execution import execute_repair_candidates, CandidateExecutionContext
from app.engine.repository_root_cause import RepairCandidate

def candidate(): return RepairCandidate("c1","h","s","r",("a.py",),("a.py",),.5)

def test_missing_spec_fails_closed():
    ctx=CandidateExecutionContext(None,(),{}, {},{}, {},lambda _:True,lambda _:1)
    result=execute_repair_candidates((candidate(),),context=ctx)
    assert result.selected_candidate_id is None
    assert "missing-repair-spec" in result.evaluations[0].rejection_reasons
