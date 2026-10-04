import pytest
from app.engine.candidate_patch import FileChange, build_candidate_patch, require_patch_matches_workspace

def ch(path,b,a): return FileChange(path,b,a,"modify")

def test_patch_is_deterministic():
    a=build_candidate_patch("c","w","r","base",[ch("b.py","1","2"),ch("a.py","3","4")])
    b=build_candidate_patch("c","w","r","base",[ch("a.py","3","4"),ch("b.py","1","2")])
    assert a.patch_digest==b.patch_digest
    assert [x.path for x in a.changes]==["a.py","b.py"]

def test_patch_must_match_candidate_workspace_baseline():
    p=build_candidate_patch("c","w","r","base",[ch("a.py","1","2")])
    with pytest.raises(ValueError,match="candidate-patch-baseline-mismatch"):
        require_patch_matches_workspace(p,candidate_id="c",workspace_id="other",
            source_revision="r",base_digest="base")

def test_invalid_identity_fails_closed():
    with pytest.raises(ValueError,match="missing-candidate-patch-identity"):
        build_candidate_patch("","","","",())
