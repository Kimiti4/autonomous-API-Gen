import pytest
from app.engine.evidence_bounded_learning import LearningRecord
from app.engine.learning_recommendations import derive_learning_recommendations,authorize_recommendation_as_current

def rec():
 return LearningRecord("L-1","P-1","repair","Use bounded retry","passed",("E-HIST",),"D-1")
def test_learning_is_advisory():
 r=derive_learning_recommendations((rec(),),project_id="P-1")
 assert r[0].status=="advisory-only"
 assert r[0].historical_evidence==("E-HIST",)
def test_history_cannot_become_current_without_current_evidence():
 r=derive_learning_recommendations((rec(),),project_id="P-1")[0]
 with pytest.raises(ValueError): authorize_recommendation_as_current(r,())
