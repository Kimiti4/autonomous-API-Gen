import pytest
from app.engine.candidate_workspaces import plan_candidate_workspaces, require_isolated_workspace

def test_candidates_get_distinct_isolated_workspaces():
    p=plan_candidate_workspaces("abc",[("a.py","x=1")],["c1","c2"])
    assert len({w.workspace_id for w in p.workspaces})==2
    assert all(w.isolated for w in p.workspaces)

def test_workspace_identity_is_deterministic():
    a=plan_candidate_workspaces("abc",[("a.py","x=1")],["c1","c2"])
    b=plan_candidate_workspaces("abc",[("a.py","x=1")],["c2","c1"])
    assert a.digest==b.digest
    assert [x.workspace_id for x in a.workspaces]==[x.workspace_id for x in b.workspaces]

def test_non_isolated_workspace_fails_closed():
    p=plan_candidate_workspaces("abc",[("a.py","x=1")],["c1"])
    w=p.workspaces[0]
    from dataclasses import replace
    with pytest.raises(ValueError,match="non-isolated-candidate-workspace:c1"):
        require_isolated_workspace(replace(w,isolated=False))
