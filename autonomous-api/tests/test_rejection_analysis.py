import pytest

from app.engine.pareto_architecture import ArchitectureScore, Objective
from app.engine.rejection_analysis import (
    derive_counterfactual_requirements,
    record_rejection,
)


OBJECTIVES = (
    Objective("quality", "maximize"),
    Objective("risk", "minimize"),
)


def score(name, quality, risk, evidence="evidence"):
    return ArchitectureScore(name, {"quality": quality, "risk": risk}, (evidence,))


def test_records_evidence_backed_pareto_rejection():
    frontier = score("frontier", 0.95, 0.10)
    candidate = score("candidate", 0.90, 0.20)

    rejection = record_rejection(
        candidate,
        reasons=("successor-dominated",),
        frontier_scores=(frontier,),
        objectives=OBJECTIVES,
    )

    assert rejection.status == "rejected"
    assert rejection.reasons == ("successor-dominated",)
    assert rejection.frontier == ("frontier",)
    assert rejection.evidence == ("evidence",)


def test_derives_necessary_counterfactual_thresholds():
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

    assert {(r.objective, r.required_value, r.delta) for r in requirements} == {
        ("quality", 0.95, 0.05),
        ("risk", 0.10, 0.10),
    }


def test_counterfactual_is_explicitly_necessary_not_admission_guarantee():
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

    assert all(r.evidence == ("evidence",) for r in requirements)


def test_rejection_requires_evidence_and_reason():
    candidate = ArchitectureScore("candidate", {"quality": 0.9, "risk": 0.2}, ())
    frontier = score("frontier", 0.95, 0.1)

    with pytest.raises(ValueError, match="rejection-score-requires-evidence"):
        record_rejection(
            candidate,
            reasons=("successor-dominated",),
            frontier_scores=(frontier,),
            objectives=OBJECTIVES,
        )

    with pytest.raises(ValueError, match="rejection-requires-reason"):
        record_rejection(
            frontier,
            reasons=(),
            frontier_scores=(frontier,),
            objectives=OBJECTIVES,
        )


def test_non_dominated_candidate_has_no_counterfactual_requirements():
    frontier = score("frontier", 0.95, 0.10)
    candidate = score("candidate", 0.90, 0.05)

    rejection = record_rejection(
        candidate,
        reasons=("policy-rejected",),
        frontier_scores=(frontier,),
        objectives=OBJECTIVES,
    )
    assert derive_counterfactual_requirements(
        rejection, (frontier,), OBJECTIVES
    ) == ()
