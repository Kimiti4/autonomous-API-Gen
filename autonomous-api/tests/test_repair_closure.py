import pytest

from app.engine.cross_domain_evolution import CoEvolutionEvent, CoEvolutionResult, DomainChange
from app.engine.evolution_population import ArchitectureLineage, EvolutionMember
from app.engine.fullstack_genome import *
from app.engine.pareto_architecture import ArchitectureScore, Objective
from app.engine.repair_closure import (
    SuccessorDomainVerification,
    close_repair_and_dependencies,
    admit_repaired_candidate,
)
from app.engine.repair_coevolution import RepairCandidate, RepairExecution, Counterexample
from app.engine.verification_plans import GateResult, VerificationReport


def parent():
    return EvolutionMember(
        ArchitectureLineage("parent", (), 0, ("parent-evidence",)),
        ArchitectureScore("parent", {"quality": 1.0, "risk": 5.0}, ("parent-evidence",)),
    )


def failed_result():
    event = CoEvolutionEvent(
        "evt-close",
        "parent",
        (
            DomainChange("frontend", "f1", ("state-integrity",)),
            DomainChange("backend", "b1", ("api-contract",)),
        ),
        ("impact",),
    )
    reports = (
        VerificationReport(
            "f1",
            (GateResult("frontend:state-integrity", "state-integrity", False, ("cx:state",)),),
            False,
        ),
        VerificationReport(
            "b1",
            (GateResult("backend:api-contract", "api-contract", True, ("api",)),),
            True,
        ),
    )
    return CoEvolutionResult(event, "child-old", reports, False)


def repair(domain, mutation_id):
    report = VerificationReport(
        mutation_id,
        (GateResult(f"{domain}:state-integrity", "state-integrity", True, ("repair",)),),
        True,
    )
    return RepairExecution(
        RepairCandidate(mutation_id, mutation_id, domain, "repair", ("state-integrity",)),
        None,
        report,
    )


def test_dependency_closure_invalidates_backend_after_frontend_failure():
    result = failed_result()
    closure = close_repair_and_dependencies(
        result,
        (repair("frontend", "f1"),),
        {"frontend": ("backend",)},
        (
            SuccessorDomainVerification(
                "backend",
                "b1",
                VerificationReport(
                    "b1",
                    (GateResult("backend:api-contract", "api-contract", True, ("reverify",)),),
                    True,
                ),
            ),
        ),
        successor_architecture_id="child-new",
    )

    assert closure.admissible
    assert closure.invalidation.invalidated_domains == ("backend", "frontend")
    assert closure.successor_architecture_id == "child-new"


def test_missing_dependent_reverification_blocks_admission():
    result = failed_result()
    closure = close_repair_and_dependencies(
        result,
        (repair("frontend", "f1"),),
        {"frontend": ("backend",)},
        (),
        successor_architecture_id="child-new",
    )
    assert not closure.admissible
    assert "missing-dependent-reverification:backend" in closure.residuals


def test_dominated_successor_is_not_admitted():
    result = failed_result()
    closure = close_repair_and_dependencies(
        result,
        (repair("frontend", "f1"),),
        {"frontend": ()},
        (),
        successor_architecture_id="child-new",
    )
    score = ArchitectureScore("child-new", {"quality": 0.5, "risk": 6.0}, ("successor-evidence",))
    with pytest.raises(ValueError, match="successor-dominated"):
        admit_repaired_candidate(
            parent(),
            closure,
            score,
            1,
            (Objective("quality", "maximize"), Objective("risk", "minimize")),
        )


def test_frontier_successor_is_admitted():
    result = failed_result()
    closure = close_repair_and_dependencies(
        result,
        (repair("frontend", "f1"),),
        {"frontend": ()},
        (),
        successor_architecture_id="child-new",
    )
    score = ArchitectureScore("child-new", {"quality": 1.2, "risk": 4.0}, ("successor-evidence",))
    child = admit_repaired_candidate(
        parent(),
        closure,
        score,
        1,
        (Objective("quality", "maximize"), Objective("risk", "minimize")),
    )
    assert child.lineage.parent_ids == ("parent",)
    assert child.lineage.generation == 1
