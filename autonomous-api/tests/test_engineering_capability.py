from app.engineering_capability import capability_for

def test_capability_inherits_quality_obligations():
    for role in ("frontend", "backend", "fullstack"):
        c = capability_for(role)
        assert c.obligation_ids
        assert c.exploration_allowed
        assert not c.framework_prescription

def test_profiles_remain_role_specific():
    assert capability_for("frontend").obligation_ids != capability_for("backend").obligation_ids
