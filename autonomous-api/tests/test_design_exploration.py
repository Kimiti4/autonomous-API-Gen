from app.engine.design_exploration import (
    EngineeringDesign, candidate_gaps, prepare_exploration,
)
from app.engine.engineering_quality import EngineeringDiscipline


def test_exploration_does_not_force_one_architecture():
    result = prepare_exploration(
        EngineeringDiscipline.FULLSTACK,
        (
            EngineeringDesign("A", "server-rendered", ("traffic known",), ("cache risk",), ("FE-ARCH",)),
            EngineeringDesign("B", "client-heavy", ("API stable",), ("state risk",), ("BE-DOMAIN",)),
        ),
    )
    assert len(result.candidates) == 2
    assert not result.unresolved


def test_exploration_exposes_quality_gaps_without_scoring_designs():
    result = prepare_exploration(
        EngineeringDiscipline.FRONTEND,
        (EngineeringDesign("A", "novel UI", ("unknown",), ("perf risk",), ("FE-ARCH",)),),
    )
    assert "FE-ARCH" not in candidate_gaps(result)["A"]
    assert any("diversity" in x for x in result.unresolved)
