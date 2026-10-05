import pytest
from app.engine.scope_authorization import MutationIntent
from app.engine.scope_discipline import RequiredWorkItem,authorize_required_work,require_no_scope_creep,release_suggestions_only_after_certification

def test_unrequested_feature_is_blocked():
 d=authorize_required_work(
   (MutationIntent("frontend","add","login"),MutationIntent("frontend","add","dark-mode")),
   (RequiredWorkItem("R-1","login","login"),))
 assert len(d.authorized)==1
 assert d.rejected[0].target=="dark-mode"
 with pytest.raises(ValueError,match="scope-creep-blocked"):
  require_no_scope_creep(d)

def test_certified_project_can_release_optional_suggestions():
 assert release_suggestions_only_after_certification(certified=False,suggestions={"x":"reason"})==()
 assert release_suggestions_only_after_certification(certified=True,suggestions={"x":"reason"})==(("x","reason"),)

def test_blank_suggestion_reason_is_not_released():
 assert release_suggestions_only_after_certification(certified=True,suggestions={"x":""})==()
