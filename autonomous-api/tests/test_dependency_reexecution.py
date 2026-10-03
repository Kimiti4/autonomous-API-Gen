import pytest

from app.engine.cross_domain_evolution import CoEvolutionEvent, CoEvolutionResult, DomainChange
from app.engine.fullstack_genome import *
from app.engine.repair_coevolution import RepairCandidate, RepairExecution
from app.engine.repair_closure import close_repair_and_dependencies
from app.engine.dependency_reexecution import execute_dependent_reverification
from app.engine.verification_plans import GateResult, VerificationReport
from app.engine.specialized_mutations import backend_mutation, frontend_mutation


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
        "evt-auto",
        "parent",
        (
            DomainChange("frontend", "f1", ("state-integrity",)),
            DomainChange("backend", "b1", ("api-contract", "effect-safety", "failure-recovery")),
        ),
        ("impact",),
    )
    reports = (
        VerificationReport(
            "f1",
            (GateResult("frontend:state-integrity", "state-integrity", False, ("cx",)),),
            False,
        ),
        VerificationReport(
            "b1",
            (GateResult("backend:api-contract", "api-contract", True, ("old",)),
             GateResult("backend:effect-safety", "effect-safety", True, ("old",)),
             GateResult("backend:failure-recovery", "failure-recovery", True, ("old",))),
            True,
        ),
    )
    return CoEvolutionResult(event, "old", reports, False)


def frontend_repair():
    return RepairExecution(
        RepairCandidate("f1", "f1-repair", "frontend", "repair", ("state-integrity",)),
        genome(),
        VerificationReport(
            "f1-repair",
            (GateResult("frontend:state-integrity", "state-integrity", True, ("repair",)),),
            True,
        ),
    )


def backend_spec():
    return backend_mutation(
        "b1-reverify",
        ("backend.api",),
        "reverify backend after frontend repair",
        ("reverify-mutation",),
        lambda g: g,
    )


def test_automatically_reexecutes_downstream_domain():
    result = failed_result()
    spec = backend_spec()
    out = execute_dependent_reverification(
        result,
        (frontend_repair(),),
        {"frontend": ("backend",)},
        (spec,),
        {
            "api-contract": lambda _: True,
            "effect-safety": lambda _: True,
            "failure-recovery": lambda _: True,
        },
        {},
        {
            "api-contract": ("fresh:contract",),
            "effect-safety": ("fresh:effect",),
            "failure-recovery": ("fresh:recovery",),
        },
        successor_architecture_id="successor",
    )

    assert [x.domain for x in out.executions] == ["backend"]
    assert out.executions[0].verification.passed
    assert out.closure.admissible
    assert out.closure.successor_architecture_id == "successor"


def test_missing_downstream_operator_blocks_execution():
    with pytest.raises(ValueError, match="missing-dependent-mutation:backend"):
        execute_dependent_reverification(
            failed_result(),
            (frontend_repair(),),
            {"frontend": ("backend",)},
            (),
            {},
            {},
            {},
            successor_architecture_id="successor",
        )
