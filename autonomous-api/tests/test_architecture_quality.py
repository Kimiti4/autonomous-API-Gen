from app.engine.architecture_quality import evaluate_candidate
from app.engine.engineering_deliberation import ArchitectureAlternative
from app.engine.quality_profiles import profile_for

def test_frontend_candidate_is_evaluated_against_frontend_obligations():
    c=ArchitectureAlternative(
      "A","accessible responsive frontend with user interaction and state correctness",
      benefits=("performance", "maintainable modular components"),
      risks=("security risk",), assumptions=("testing required",)
    )
    r=evaluate_candidate(c, profile_for("frontend"))
    assert "FE-A11Y" in r.satisfied
    assert "FE-PERF" in r.satisfied
    assert "FE-SEC" in r.satisfied
    assert "FE-TEST" in r.satisfied

def test_backend_candidate_missing_obligations_is_not_implicitly_accepted():
    c=ArchitectureAlternative("A","simple API")
    r=evaluate_candidate(c, profile_for("backend"))
    assert r.missing
    assert "BE-SEC" in r.missing
