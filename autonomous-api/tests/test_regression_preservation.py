import pytest
from app.engine.regression_preservation import evaluate_regression_preservation,require_regression_preservation

def test_previous_requirements_need_fresh_evidence():
 r=evaluate_regression_preservation(("R1","R2"),{"R1":{"passed":True,"evidence_ids":("E1",)},"R2":{"passed":True,"evidence_ids":("E2",)}})
 assert r.preserved
def test_regression_blocks_admission():
 r=evaluate_regression_preservation(("R1",),{"R1":{"passed":False,"evidence_ids":("E1",)}})
 assert not r.preserved
 with pytest.raises(ValueError): require_regression_preservation(r)
def test_missing_evidence_is_not_a_pass():
 r=evaluate_regression_preservation(("R1",),{"R1":{"passed":True}})
 assert not r.preserved
