import pytest
from app.engine.evidence_bounded_learning import record_learning,query_learning,authorize_learning_as_fact

def rec():
 return record_learning(record_id="L-1",project_id="P-1",kind="repair",statement="retry fix passed",outcome="passed",evidence_ids=("E-1",),source_digest="D-1")
def test_learning_requires_evidence():
 assert rec().confidence=="observed"
 with pytest.raises(ValueError): record_learning(record_id="L",project_id="P",kind="repair",statement="x",outcome="y",evidence_ids=(),source_digest="D")
def test_memory_is_advisory():
 assert query_learning((rec(),),"P-1").advisory_only
def test_history_cannot_certify_current_state():
 with pytest.raises(ValueError): authorize_learning_as_fact(rec(),())
