from app.engine.architecture_ir import generate_baseline_candidates
from app.engine.architecture_obligations import derive_architecture_obligations, map_obligations
from app.engine.architecture_selection import (
    ArchitectureSelectionRequest, authorize_selection, evaluate_candidate,
)
from app.engine.requirement_ir import Requirement, RequirementKind, build_requirement_graph
from app.engine.requirement_isr import project_to_isr


def isr():
    return project_to_isr(build_requirement_graph([
        Requirement("R1", "Transfer must not execute twice", RequirementKind.FUNCTIONAL),
    ]))


def test_candidate_is_admissible_only_with_explicit_mappings():
    i = isr()
    candidate = generate_baseline_candidates(i)[0]
    obligations = derive_architecture_obligations(i)
    mappings = map_obligations(obligations, ("COMP-CORE",), satisfied=True, rationale="supported")
    evaluation = evaluate_candidate(candidate, obligations, mappings)
    assert evaluation.admissible
    assert evaluation.satisfied_obligations == 1


def test_selection_does_not_implicitly_rank_candidates():
    i = isr()
    candidates = generate_baseline_candidates(i)
    obligations = derive_architecture_obligations(i)
    evaluations = tuple(
        evaluate_candidate(c, obligations, map_obligations(obligations, (c.components[0].component_id,), satisfied=True, rationale="supported"))
        for c in candidates
    )
    request = ArchitectureSelectionRequest("SEL-001", tuple(c.architecture_id for c in candidates))
    selection = authorize_selection(request, evaluations, selected_candidate_id=candidates[1].architecture_id,
                                    authorized_by="human:operator", rationale="explicitly selected for this workload")
    assert selection.selected_candidate_id == candidates[1].architecture_id


def test_inadmissible_candidate_cannot_be_selected():
    i = isr()
    candidate = generate_baseline_candidates(i)[0]
    obligations = derive_architecture_obligations(i)
    evaluation = evaluate_candidate(candidate, obligations, ())
    request = ArchitectureSelectionRequest("SEL-002", (candidate.architecture_id,))
    try:
        authorize_selection(request, (evaluation,), selected_candidate_id=candidate.architecture_id,
                            authorized_by="human:operator", rationale="selection")
    except ValueError as exc:
        assert "inadmissible" in str(exc)
    else:
        raise AssertionError("inadmissible architecture must not be selectable")
