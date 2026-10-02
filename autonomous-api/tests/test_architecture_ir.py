from app.engine.architecture_ir import (
    ArchitectureCandidate, ArchitectureComponent, evaluate_architecture,
    generate_baseline_candidates, validate_architecture,
)
from app.engine.requirement_ir import Requirement, RequirementKind, build_requirement_graph
from app.engine.requirement_isr import project_to_isr


def make_isr():
    g = build_requirement_graph([
        Requirement("R1", "Transfer must not execute twice", RequirementKind.FUNCTIONAL),
    ])
    return project_to_isr(g)


def test_baseline_generator_produces_multiple_neutral_candidates():
    candidates = generate_baseline_candidates(make_isr())
    assert len(candidates) == 2
    assert all("FastAPI" not in str(c.to_dict()) for c in candidates)


def test_architecture_requires_failure_modes_and_tradeoffs():
    c = ArchitectureCandidate("A", (ArchitectureComponent("C", "x", "b"),), (), "x", (), (), "r")
    assert "architecture has no failure modes" in validate_architecture(c)
    assert "architecture has no explicit trade-offs" in validate_architecture(c)


def test_unsatisfied_invariant_prevents_admissibility():
    c = generate_baseline_candidates(make_isr())[0]
    evaluation = evaluate_architecture(c, make_isr())
    assert not evaluation.admissible
    assert evaluation.unsatisfied_invariants == ("I-R1",)
