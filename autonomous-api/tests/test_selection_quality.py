from app.engine.architecture_quality import evaluate_candidates
from app.engine.engineering_deliberation import ArchitectureAlternative, EngineeringDeliberation
from app.engine.selection_quality import selection_readiness
from app.engine.quality_profiles import profile_for

def test_selection_is_blocked_when_candidate_quality_is_incomplete():
    d=EngineeringDeliberation("api",(),(
      ArchitectureAlternative("A","simple API"),
      ArchitectureAlternative("B","secure tested API with performance and reliability"),
    ),(),())
    ev=evaluate_candidates(d.alternatives, profile_for("backend"))
    r=selection_readiness(d,ev)
    assert not r.ready
    assert r.findings

def test_selection_cannot_bypass_missing_evaluation():
    d=EngineeringDeliberation("api",(),(
      ArchitectureAlternative("A","secure tested API"),
      ArchitectureAlternative("B","secure tested API"),
    ),(),(),selected_alternative="A",selection_rationale="evidence")
    r=selection_readiness(d, ())
    assert not r.ready
