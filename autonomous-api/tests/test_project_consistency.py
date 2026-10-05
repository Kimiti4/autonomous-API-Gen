import pytest
from app.engine.project_consistency import evaluate_project_consistency,require_project_consistency

def test_complete_consistency_requires_all_layers():
 r=evaluate_project_consistency(("O1",),{"O1":1},{"O1":1},{"O1":{"passed":True,"evidence_ids":("E",)}})
 assert r.consistent
def test_missing_layer_blocks_certification():
 r=evaluate_project_consistency(("O1",),{"O1":1},{},{"O1":{"passed":True,"evidence_ids":("E",)}})
 assert not r.consistent
 with pytest.raises(ValueError): require_project_consistency(r)
def test_failed_verification_is_not_consistent():
 r=evaluate_project_consistency(("O1",),{"O1":1},{"O1":1},{"O1":{"passed":False,"evidence_ids":("E",)}})
 assert not r.consistent
