import pytest

from app.engine.counterfactual_plan import materialize_counterfactual_plan
from app.engine.pareto_architecture import ArchitectureScore, Objective
from app.engine.rejection_analysis import (
    derive_counterfactual_requirements,
    record_rejection,
)


OBJECTIVES = (
    Objective("quality", "maximize"),
    Objective("risk", "minimize"),
)


def score(name, quality, risk):
    return ArchitectureScore(name, {"quality": quality, "risk": risk}, ("measurement:evidence",))


def test_materializes_bounded_improvement_plan():
    frontier = score("frontier", 0.95, 0.10)
    candidate = score("candidate", 0.90, 0.20)
    rejection = record_rejection(
        candidate,
        reasons=("successor-dominated",),
        frontier_scores=(frontier,),
        objectives=OBJECTIVES,
    )
    requirements = derive_counterfactual_requirements(
        rejection, (frontier,), OBJECTIVES
    )
    plan = materialize_counterfactual_plan(rejection, requirements)

    assert plan.candidate_architecture_id == "candidate"
    assert plan.bounded
    assert plan.rejection_reasons == ("successor-dominated",)
    assert [(x.objective, x.target_value) for x in plan.improvements] == [
        ("quality", 0.95),
        ("risk", 0.10),
    ]


def test_plan_preserves_evidence_and_does_not_claim_admission():
    frontier = score("frontier", 0.95, 0.10)
    candidate = score("candidate", 0.90, 0.20)
    rejection = record_rejection(
        candidate,
        reasons=("successor-dominated",),
        frontier_scores=(frontier,),
        objectives=OBJECTIVES,
    )
    requirements = derive_counterfactual_requirements(
        rejection, (frontier,), OBJECTIVES
    )
    plan = materialize_counterfactual_plan(rejection, requirements)

    assert all(x.evidence == ("measurement:evidence",) for x in plan.improvements)
    assert not hasattr(plan, "admitted")


def test_plan_fails_closed_for_non_rejection():
    candidate = score("candidate", 0.95, 0.10)
    rejection = type("R", (), {
        "status": "admitted",
        "candidate_architecture_id": "candidate",
        "reasons": (),
    })()
    with pytest.raises(ValueError, match="counterfactual-plan-requires-rejection"):
        materialize_counterfactual_plan(rejection, ())


def test_plan_fails_closed_on_mismatched_requirement():
    frontier = score("frontier", 0.95, 0.10)
    candidate = score("candidate", 0.90, 0.20)
    rejection = record_rejection(
        candidate,
        reasons=("successor-dominated",),
        frontier_scores=(frontier,),
        objectives=OBJECTIVES,
    )
    requirements = derive_counterfactual_requirements(
        rejection, (frontier,), OBJECTIVES
    )
    forged = tuple(
        type(requirements[0])(
            "other-candidate",
            requirements[0].objective,
            requirements[0].direction,
            requirements[0].current_value,
            requirements[0].required_value,
            requirements[0].delta,
            requirements[0].evidence,
        )
        for _ in [0]
    )
    with pytest.raises(ValueError, match="counterfactual-requirement-candidate-mismatch"):
        materialize_counterfactual_plan(rejection, forged)
