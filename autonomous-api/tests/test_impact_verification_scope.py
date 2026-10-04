import pytest
from app.engine.repository_impact_analysis import analyze_finding_impact
from app.engine.impact_verification_scope import derive_impact_verification_scope, require_impact_verification

FILES=(("core.py","x=1"),("service.py","from core import x"),("api.py","from service import x"))

def test_impact_scope_contains_source_and_dependents():
    impact=analyze_finding_impact("f1","core.py",FILES)
    scope=derive_impact_verification_scope(impact)
    assert scope.required_paths==("api.py","core.py","service.py")

def test_missing_affected_verification_fails_closed():
    impact=analyze_finding_impact("f1","core.py",FILES)
    scope=derive_impact_verification_scope(impact)
    with pytest.raises(ValueError,match="missing-impact-verification:api.py"):
        require_impact_verification(scope,("core.py","service.py"))

def test_complete_scope_verification_passes():
    impact=analyze_finding_impact("f1","core.py",FILES)
    scope=derive_impact_verification_scope(impact)
    require_impact_verification(scope,scope.required_paths)
