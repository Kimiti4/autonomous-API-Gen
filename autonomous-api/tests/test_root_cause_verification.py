import pytest
from app.engine.repository_root_cause import RootCauseHypothesis
from app.engine.root_cause_verification import verify_root_cause,require_verified_root_cause

def h(): return RootCauseHypothesis("H1","F1","code-quality","risk",("scan",),.4)
def test_hypothesis_requires_current_evidence():
 r=verify_root_cause(h(),{"F1":True},("E1",)); assert r.confirmed
def test_missing_current_observation_blocks():
 r=verify_root_cause(h(),{"F1":False},("E1",)); assert not r.confirmed
 with pytest.raises(ValueError): require_verified_root_cause(r)
def test_missing_evidence_blocks():
 r=verify_root_cause(h(),{"F1":True},()); assert not r.confirmed
