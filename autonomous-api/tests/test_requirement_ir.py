from app.engine.requirement_ir import (
    AcceptanceCriterion, Requirement, RequirementGraph, RequirementKind,
    build_requirement_graph, detect_ambiguity,
)


def ac(i): return AcceptanceCriterion(i, "observable condition")


def test_requirement_graph_is_deterministic_and_traceable():
    graph = build_requirement_graph([
        Requirement("R2", "Store result", RequirementKind.FUNCTIONAL, depends_on=("R1",), acceptance_criteria=(ac("AC2"),)),
        Requirement("R1", "Authenticate caller", RequirementKind.SECURITY, acceptance_criteria=(ac("AC1"),)),
    ])
    assert graph.topological_order() == ["R1", "R2"]
    assert graph.traceability()["R2"]["depends_on"] == ["R1"]


def test_missing_dependency_fails_validation():
    graph = RequirementGraph()
    graph.add(Requirement("R1", "Do X", RequirementKind.FUNCTIONAL, depends_on=("R404",), acceptance_criteria=(ac("AC1"),)))
    issues = graph.validate()
    assert any(i.severity == "error" for i in issues)
    try:
        graph.topological_order()
    except ValueError:
        pass
    else:
        raise AssertionError("invalid graph must not be ordered")


def test_conflicting_dependency_is_detected():
    graph = RequirementGraph()
    graph.add(Requirement("R1", "A", RequirementKind.FUNCTIONAL, acceptance_criteria=(ac("AC1"),)))
    graph.add(Requirement("R2", "B", RequirementKind.FUNCTIONAL, depends_on=("R1",), conflicts_with=("R1",), acceptance_criteria=(ac("AC2"),)))
    assert any("contradiction" in i.message for i in graph.validate())


def test_cycle_is_rejected():
    graph = RequirementGraph()
    graph.add(Requirement("R1", "A", RequirementKind.FUNCTIONAL, depends_on=("R2",), acceptance_criteria=(ac("AC1"),)))
    graph.add(Requirement("R2", "B", RequirementKind.FUNCTIONAL, depends_on=("R1",), acceptance_criteria=(ac("AC2"),)))
    try:
        graph.topological_order()
    except ValueError as exc:
        assert "cycle" in str(exc)
    else:
        raise AssertionError("cycle must be rejected")


def test_ambiguity_detection_does_not_claim_resolution():
    assert "unquantified:fast" in detect_ambiguity("The API must be fast")
    assert detect_ambiguity("The API must answer within 200ms") == []
