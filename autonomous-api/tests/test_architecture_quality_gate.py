from app.architecture_quality_gate import evaluate_architecture_quality
from app.engineering_deliberation import ArchitectureAlternative, EngineeringDeliberation

def test_quality_gate_evaluates_every_candidate():
    d = EngineeringDeliberation(
        "frontend",
        (),
        (ArchitectureAlternative("A","accessible user flow with performance testing"),
         ArchitectureAlternative("B","accessible user flow with performance testing")),
        (), ()
    )
    g = evaluate_architecture_quality("frontend", d)
    assert {x.alternative_id for x in g.evaluations} == {"A", "B"}

def test_quality_gate_rejects_unknown_role():
    d = EngineeringDeliberation("x", (), (), (), ())
    try:
        evaluate_architecture_quality("mobile", d)
        assert False
    except ValueError as e:
        assert "unsupported" in str(e)
