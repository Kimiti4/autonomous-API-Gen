import pytest

from app.engine.counterfactual_plan import materialize_counterfactual_plan
from app.engine.counterfactual_work import materialize_counterfactual_work
from app.engine.pareto_architecture import ArchitectureScore, Objective
from app.engine.rejection_analysis import derive_counterfactual_requirements, record_rejection


OBJECTIVES = (Objective("quality", "maximize"), Objective("risk", "minimize"))


def score(name, quality, risk):
    return ArchitectureScore(name, {"quality": quality, "risk": risk}, ("measurement:evidence",))


def plan():
    frontier = score("frontier", 0.95, 0.10)
    candidate = score("candidate", 0.90, 0.20)
    rejection = record_rejection(
        candidate, reasons=("successor-dominated",),
        frontier_scores=(frontier,), objectives=OBJECTIVES,
    )
    requirements = derive_counterfactual_requirements(
        rejection, (frontier,), OBJECTIVES
    )
    return materialize_counterfactual_plan(rejection, requirements)


def test_materializes_executable_work_with_acceptance_properties():
    work = materialize_counterfactual_work(
        plan(),
        work_id_prefix="cf",
        acceptance_properties_by_objective={
            "quality": ("quality-threshold",),
            "risk": ("risk-threshold",),
        },
    )
    assert work.bounded
    assert [item.work_id for item in work.work_items] == ["cf:1", "cf:2"]
    assert [item.objective for item in work.work_items] == ["quality", "risk"]
    assert work.work_items[0].acceptance_properties == ("quality-threshold",)


def test_work_preserves_evidence_and_targets():
    work = materialize_counterfactual_work(
        plan(),
        work_id_prefix="repair",
        acceptance_properties_by_objective={
            "quality": ("quality-threshold",),
            "risk": ("risk-threshold",),
        },
    )
    assert all(item.evidence == ("measurement:evidence",) for item in work.work_items)
    assert [(i.current_value, i.target_value) for i in work.work_items] == [
        (0.9, 0.95), (0.2, 0.1)
    ]


def test_work_requires_acceptance_properties():
    with pytest.raises(ValueError, match="counterfactual-work-missing-acceptance-properties:risk"):
        materialize_counterfactual_work(
            plan(),
            work_id_prefix="cf",
            acceptance_properties_by_objective={"quality": ("quality-threshold",)},
        )


def test_work_requires_bounded_plan():
    p = plan()
    unbounded = type(p)(p.candidate_architecture_id, p.rejection_reasons, p.improvements, False)
    with pytest.raises(ValueError, match="counterfactual-work-requires-bounded-plan"):
        materialize_counterfactual_work(
            unbounded, work_id_prefix="cf",
            acceptance_properties_by_objective={"quality": ("q",), "risk": ("r",)},
        )
