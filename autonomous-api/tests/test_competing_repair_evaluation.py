from app.engine.repository_root_cause import RepairCandidate
from app.engine.repair_candidate_selection import CandidateEvaluation
from app.engine.competing_repair_evaluation import (
    evaluate_competing_repairs,
    select_competing_repair,
)


def candidate(i):
    return RepairCandidate(i, "H", "strategy", "reason", ("x",), ("x",), .5)


def evaluation(i, verification=1.0, measurement=1.0, evidence=("E",)):
    return CandidateEvaluation(i, True, verification, True, measurement, evidence)


def assessed(candidates, evaluations, evidence=None, dimensions=None):
    ids = [c.candidate_id for c in candidates]
    evidence = evidence or {i: ("E",) for i in ids}
    dimensions = dimensions or {i: ("verification", "measurement") for i in ids}
    return evaluate_competing_repairs(
        candidates, evaluations,
        current_evidence=evidence,
        objective_dimensions=dimensions,
    )


def test_selects_unique_best_current_evidence_candidate():
    cs = (candidate("A"), candidate("B"))
    result = select_competing_repair(
        assessed(cs, (evaluation("A", 2, 1), evaluation("B", 1, 2)))
    )
    assert result.selected_candidate_id == "A"
    assert result.status == "selected-evidenced-candidate"
    assert result.compared_candidate_ids == ("A", "B")


def test_does_not_break_tie_by_candidate_id():
    cs = (candidate("A"), candidate("B"))
    result = select_competing_repair(
        assessed(cs, (evaluation("A", 2, 2), evaluation("B", 2, 2)))
    )
    assert result.selected_candidate_id is None
    assert result.status == "unknown-insufficient-discrimination"


def test_stale_or_incomplete_evidence_is_not_comparable():
    cs = (candidate("A"), candidate("B"))
    evaluations = (evaluation("A", 3, 3, ("OLD",)), evaluation("B", 1, 1))
    result = select_competing_repair(
        assessed(
            cs,
            evaluations,
            evidence={"A": ("CURRENT",), "B": ("E",)},
        )
    )
    assert result.selected_candidate_id == "B"
    assert result.compared_candidate_ids == ("B",)
    assert result.status == "selected-evidenced-candidate"


def test_missing_evaluation_is_recorded_and_cannot_win():
    cs = (candidate("A"), candidate("B"))
    result = select_competing_repair(assessed(cs, (evaluation("B", 2, 2))))
    assert result.selected_candidate_id == "B"
    assert any(
        e.candidate_id == "A" and "missing-candidate-evaluation" in e.findings
        for e in result.evaluations
    )


def test_missing_current_evidence_fails_closed():
    cs = (candidate("A"),)
    result = select_competing_repair(
        assessed(cs, (evaluation("A", 2, 2)), evidence={"A": ()})
    )
    assert result.selected_candidate_id is None
    assert result.status == "unknown-no-comparable-repair"


def test_missing_objective_dimensions_fails_closed():
    cs = (candidate("A"),)
    result = select_competing_repair(
        assessed(cs, (evaluation("A", 2, 2)), dimensions={"A": ()})
    )
    assert result.selected_candidate_id is None
    assert result.status == "unknown-no-comparable-repair"
