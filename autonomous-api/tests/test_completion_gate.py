import pytest
from app.engine.completion_gate import FeatureSuggestion, assess_completion, require_project_completion, require_suggestion_evidence

def test_incomplete_project_cannot_receive_feature_suggestions():
    s=FeatureSuggestion("F-2","Extra export","Useful for users",("E-2",))
    a=assess_completion(("R-1","R-2"),{"R-1":{"implemented":True,"passed":True,"evidence_ids":("E-1",)}},True,(s,))
    assert not a.project_complete
    assert a.suggestions==()
    with pytest.raises(ValueError):
        require_project_completion(a)

def test_suggestions_are_available_only_after_e2e_certification():
    s=FeatureSuggestion("F-2","Extra export","Useful for users",("E-2",))
    a=assess_completion(("R-1",),{"R-1":{"implemented":True,"passed":True,"evidence_ids":("E-1",)}},True,(s,))
    assert a.project_complete
    assert a.suggestions==(s,)
    require_project_completion(a)

def test_suggestion_without_reason_or_evidence_fails_closed():
    with pytest.raises(ValueError): require_suggestion_evidence(FeatureSuggestion("F","X","",("E",)))
    with pytest.raises(ValueError): require_suggestion_evidence(FeatureSuggestion("F","X","why",()))
