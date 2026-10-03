import pytest

from app.engine.cross_domain_evolution import CoEvolutionEvent, CoEvolutionResult, DomainChange
from app.engine.evolution_population import ArchitectureLineage, EvolutionMember
from app.engine.fullstack_genome import *
from app.engine.pareto_architecture import ArchitectureScore
from app.engine.repair_coevolution import extract_counterexamples, build_repair_candidates, execute_repairs
from app.engine.verification_plans import GateResult, VerificationReport
from app.engine.specialized_mutations import backend_mutation


def genome():
    return FullStackGenome(
        FrontendGenome("render", "state", "interaction", "a11y", "resilience"),
        BackendGenome("service", "strong", "safe", "retry", "contract"),
        DataGenome("sql", "integrity", "expand-contract", "strong"),
        SecurityGenome("identity", "rbac", ("api",), ("audit",), "vault"),
        OperationalGenome("containers", "metrics", "rollback", "bounded"),
        "v1",
        "frontend->api->backend",
    )


def failed_result():
    event = CoEvolutionEvent(
        "evt-repair",
        "root",
        (DomainChange("backend", "b1", ("api-contract", "effect-safety")),),
        ("impact", "failed-test"),
    )
    report = VerificationReport(
        "b1",
        (
            GateResult("backend:api-contract", "api-contract", True, ("api-ok",)),
            GateResult("backend:effect-safety", "effect-safety", False, ("counterexample:effect",)),
        ),
        False,
    )
    return CoEvolutionResult(event, "child-1", (report,), False)


def repair_spec():
    return backend_mutation(
        "b1",
        ("backend.api",),
        "repair effect safety",
        ("repair-evidence",),
        lambda g: g,
    )


def test_counterexample_extracts_failed_properties_and_evidence():
    result = failed_result()
    cx = extract_counterexamples(result)

    assert len(cx) == 1
    assert cx[0].domain == "backend"
    assert cx[0].failed_properties == ("effect-safety",)
    assert cx[0].evidence == ("counterexample:effect",)


def test_missing_repair_operator_is_explicitly_bounded():
    result = failed_result()
    assert build_repair_candidates(result, ()) == ()
    with pytest.raises(ValueError, match="missing-repair-mutation:backend"):
        execute_repairs(
            result,
            None,
            genome(),
            (),
            {"api-contract": lambda _: True},
            {},
            {"api-contract": ("verify",)},
        )


def test_repair_executes_and_reverifies_failed_domain():
    result = failed_result()
    spec = repair_spec()
    verifiers = {
        "api-contract": lambda _: True,
        "effect-safety": lambda _: True,
        "failure-recovery": lambda _: True,
    }
    evidence = {
        "api-contract": ("repair:contract",),
        "effect-safety": ("repair:effect",),
        "failure-recovery": ("repair:recovery",),
    }
    repaired = execute_repairs(
        result,
        None,
        genome(),
        (spec,),
        verifiers,
        {},
        evidence,
    )

    assert repaired.passed
    assert len(repaired.repairs) == 1
    assert repaired.repairs[0].candidate.source_mutation_id == "b1"
    assert repaired.repairs[0].verification.passed
