from dataclasses import replace

import pytest

from app.engine.execute_coevolution import execute_materialized_coevolution
from app.engine.impact_discovery import ImpactRelation, ImpactRequest, discover_impact
from app.engine.impact_to_coevolution import build_coevolution_plan
from app.engine.materialize_coevolution import materialize_coevolution_work
from app.engine.specialized_mutations import backend_mutation, frontend_mutation
from app.engine.execution_policy import ExecutionPolicy
from app.engine.verification_command_planner import VerificationCommandRule
from app.engine.verification_executor import VerificationKind
from app.engine.evolution_population import ArchitectureLineage, EvolutionMember
from app.engine.pareto_architecture import ArchitectureScore
from app.engine.fullstack_genome import (
    BackendGenome,
    DataGenome,
    FrontendGenome,
    FullStackGenome,
    OperationalGenome,
    SecurityGenome,
)


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


def source():
    return EvolutionMember(
        ArchitectureLineage("root", (), 0, ("source-evidence",)),
        ArchitectureScore("root", {"quality": 1.0}, ("source-evidence",)),
    )


def plan():
    impact = discover_impact(
        ImpactRequest("frontend", ("frontend.api",), ("api-contract",)),
        (
            ImpactRelation(
                "frontend",
                "backend",
                "api-contract",
                ("impact-trace",),
            ),
        ),
    )
    return build_coevolution_plan(impact, ("frontend", "backend"), True)


def specs():
    return (
        frontend_mutation(
            "f1",
            ("frontend.api",),
            "adapt frontend",
            ("frontend-mutation-evidence",),
            lambda g: replace(g, metadata={**g.metadata, "frontend": "changed"}),
        ),
        backend_mutation(
            "b1",
            ("backend.api",),
            "adapt backend",
            ("backend-mutation-evidence",),
            lambda g: replace(g, metadata={**g.metadata, "backend": "changed"}),
        ),
    )


def verifier_map():
    properties = (
        "accessibility",
        "interaction-consistency",
        "state-integrity",
        "api-contract",
        "effect-safety",
        "failure-recovery",
    )
    return {name: (lambda _observations: True) for name in properties}


def evidence_map():
    return {
        "accessibility": ("verify:accessibility",),
        "interaction-consistency": ("verify:interaction",),
        "state-integrity": ("verify:state",),
        "api-contract": ("verify:contract",),
        "effect-safety": ("verify:effect",),
        "failure-recovery": ("verify:recovery",),
    }



def command_rule(kind):
    return VerificationCommandRule(
        kind,
        ("python", "-c", "print('scope-verified')"),
        5,
        ExecutionPolicy(("python",), max_timeout_seconds=5),
    )

def test_materialized_work_executes_each_domain_and_closes_event():
    p = plan()
    s = specs()
    work = materialize_coevolution_work(p, s)

    result = execute_materialized_coevolution(
        work,
        source(),
        genome(),
        s,
        verifier_map(),
        {},
        evidence_map(),
        event_id="evt-1",
        candidate_architecture_id="child-1",
    )

    assert result.candidate_architecture_id == "child-1"
    assert [x.domain for x in result.domain_executions] == ["backend", "frontend"]
    assert result.domain_executions[0].candidate.metadata["backend"] == "changed"
    assert result.domain_executions[1].candidate.metadata["frontend"] == "changed"
    assert result.result.passed
    assert {x.mutation_id for x in result.result.reports} == {"f1", "b1"}
    assert "impact-trace" in result.event.evidence
    assert "verify:contract" in result.event.evidence

    executable = execute_materialized_coevolution(
        work,
        source(),
        genome(),
        s,
        verifier_map(),
        {},
        evidence_map(),
        event_id="evt-verified",
        verification_command_rules=(
            command_rule(VerificationKind.BUILD),
            command_rule(VerificationKind.TEST),
            command_rule(VerificationKind.TYPECHECK),
        ),
        verification_root=str(__import__("pathlib").Path.cwd()),
        verification_workspace_id="candidate-verified",
    )
    assert executable.executable_verification is not None
    assert executable.executable_verification.evidence_digests


def test_verification_failure_is_retained_in_cross_domain_result():
    p = plan()
    s = specs()
    work = materialize_coevolution_work(p, s)
    verifiers = verifier_map()
    verifiers["effect-safety"] = lambda _observations: False

    result = execute_materialized_coevolution(
        work,
        source(),
        genome(),
        s,
        verifiers,
        {},
        evidence_map(),
        event_id="evt-2",
    )

    assert not result.result.passed
    backend = next(r for r in result.result.reports if r.mutation_id == "b1")
    assert not backend.passed


def test_uncertain_materialized_work_is_fail_closed():
    from app.engine.materialize_coevolution import ExecutableCoEvolutionWork, PlannedDomainWork

    uncertain = ExecutableCoEvolutionWork(
        "frontend",
        (PlannedDomainWork("backend", "b1", ("api-contract",), "impact"),),
        ("trace",),
        True,
    )

    with pytest.raises(ValueError, match="cannot-execute-uncertain-coevolution-work"):
        execute_materialized_coevolution(
            uncertain,
            source(),
            genome(),
            specs(),
            verifier_map(),
            {},
            evidence_map(),
            event_id="evt-3",
        )
