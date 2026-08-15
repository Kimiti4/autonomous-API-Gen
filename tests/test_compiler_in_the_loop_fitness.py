"""
Tests for Phase 21.2 compiler-in-the-loop fitness evaluation.
"""

from evolution.compiler_fitness import (
    BackendCompilationResult,
    CompilerFitnessEvaluator,
    CompilerFitnessPolicy,
    StaticCompilerGateway,
)
from evolution.compiler_loop import CompilerAwareMultiCandidateEngine
from evolution.engine import EvolutionPolicy, SelfEvolutionEngine
from evolution.governance import StaticGovernanceClient
from evolution.models import (
    CandidateArchitecture,
    EvolutionProposalRequest,
    EvolutionTargetType,
    GenerateCandidatesRequest,
    MutationOperationSpec,
    MutationOperationType,
    MutationSpec,
    utcnow,
)


def base_isr() -> dict:
    return {
        "isr_id": "isr_billing_001",
        "version": "1.0.0",
        "name": "Billing System",
        "domains": [
            {
                "name": "billing",
                "services": [
                    {
                        "name": "BillingService",
                        "apis": [
                            {
                                "name": "createInvoice"
                            }
                        ],
                        "depends_on": [],
                    }
                ],
            }
        ],
        "security": {
            "authentication": "OIDC",
        },
        "observability": {
            "metrics": True,
        },
        "deployment": {
            "container": True,
        },
        "testing": {
            "unit_tests": True,
        },
    }


def base_mutation_spec() -> MutationSpec:
    return MutationSpec(
        id="mutation_add_list_invoices",
        operator="architecture_mutator",
        chromosome_family="backend",
        gene_id="billing_api_surface",
        rationale="Add invoice listing capability.",
        operations=[
            MutationOperationSpec(
                operation=MutationOperationType.ADD_ITEM,
                path="domains.0.services.0.apis",
                value={
                    "name": "listInvoices"
                },
            )
        ],
    )


def proposal_request() -> EvolutionProposalRequest:
    return EvolutionProposalRequest(
        title="Compiler-in-the-loop evolution test",
        description="Evaluate candidate architectures with compiler evidence.",
        target_type=EvolutionTargetType.APPLICATION_ARCHITECTURE,
        target_ref="billing_system",
        base_isr=base_isr(),
        mutation=base_mutation_spec(),
        high_impact=False,
        allow_breaking_changes=False,
        environment="development",
    )


def success_result(backend_id: str) -> BackendCompilationResult:
    return BackendCompilationResult(
        backend_id=backend_id,
        status="SUCCEEDED",
        artifact_count=6,
        total_bytes=2048,
        artifact_paths=[
            "app/main.py",
            "tests/test_app.py",
            "Dockerfile",
            "openapi/openapi.json",
            "migrations/0001_initial.sql",
            ".github/workflows/ci.yml",
        ],
    )


def failed_result(backend_id: str) -> BackendCompilationResult:
    return BackendCompilationResult(
        backend_id=backend_id,
        status="FAILED",
        issues=[
            "Backend compilation failed.",
        ],
    )


def make_candidate(candidate_id: str = "candidate_1") -> CandidateArchitecture:
    return CandidateArchitecture(
        id=candidate_id,
        proposal_id="proposal_1",
        mutation_spec_id="mutation_1",
        base_isr_hash="sha256:base",
        content_hash="sha256:candidate",
        isr=base_isr(),
        created_at=utcnow().isoformat(),
    )


def test_compiler_fitness_passes_when_backend_succeeds():
    gateway = StaticCompilerGateway(
        {
            "python.fastapi.foundation": success_result(
                "python.fastapi.foundation"
            ),
        }
    )

    policy = CompilerFitnessPolicy(
        backend_ids=["python.fastapi.foundation"],
        required_backend_ids=["python.fastapi.foundation"],
        require_docker=True,
        require_tests=True,
        require_openapi=True,
        require_migrations=True,
        require_ci=True,
    )

    evaluator = CompilerFitnessEvaluator(gateway, policy)

    report = evaluator.evaluate_candidate(make_candidate())

    assert report.passed is True
    assert report.objectives["compilability"] == 1.0
    assert report.objectives["deployability"] == 1.0
    assert report.objectives["test_evidence"] == 1.0
    assert report.objectives["contract_evidence"] == 1.0
    assert report.objectives["persistence_evidence"] == 1.0
    assert report.objectives["ci_evidence"] == 1.0


def test_compiler_fitness_fails_when_backend_fails():
    gateway = StaticCompilerGateway(
        {
            "python.fastapi.foundation": failed_result(
                "python.fastapi.foundation"
            ),
        }
    )

    policy = CompilerFitnessPolicy(
        backend_ids=["python.fastapi.foundation"],
        required_backend_ids=["python.fastapi.foundation"],
    )

    evaluator = CompilerFitnessEvaluator(gateway, policy)

    report = evaluator.evaluate_candidate(make_candidate())

    assert report.passed is False
    assert report.objectives["compilability"] == 0.0
    assert report.constraints["all_required_backends_succeeded"] is False


def test_compiler_aware_multi_candidate_engine():
    base_engine = SelfEvolutionEngine(
        governance_client=StaticGovernanceClient(
            decision="ALLOW",
            reason="Static governance decision.",
        ),
        policy=EvolutionPolicy(),
    )

    gateway = StaticCompilerGateway(
        {
            "python.fastapi.foundation": success_result(
                "python.fastapi.foundation"
            ),
        }
    )

    policy = CompilerFitnessPolicy(
        backend_ids=["python.fastapi.foundation"],
        required_backend_ids=["python.fastapi.foundation"],
        require_docker=True,
        require_tests=True,
    )

    multi_engine = CompilerAwareMultiCandidateEngine(
        base_engine=base_engine,
        compiler_gateway=gateway,
        policy=policy,
    )

    proposal = base_engine.propose(proposal_request(), "tester")

    multi_engine.generate_candidates(
        proposal.id,
        GenerateCandidatesRequest(
            mutations=[],
            include_base_mutation=True,
        ),
        "tester",
    )

    evaluations = multi_engine.evaluate_candidates(
        proposal.id,
        "tester",
    )

    assert len(evaluations) == 1

    evaluation = evaluations[0]

    assert evaluation.feasible is True
    assert evaluation.fitness is not None
    assert evaluation.fitness.passed is True
    assert evaluation.fitness.objectives["compiler_compilability"] == 1.0


def test_compiler_aware_engine_marks_infeasible_when_compilation_fails():
    base_engine = SelfEvolutionEngine(
        governance_client=StaticGovernanceClient(
            decision="ALLOW",
            reason="Static governance decision.",
        ),
        policy=EvolutionPolicy(),
    )

    gateway = StaticCompilerGateway(
        {
            "python.fastapi.foundation": failed_result(
                "python.fastapi.foundation"
            ),
        }
    )

    policy = CompilerFitnessPolicy(
        backend_ids=["python.fastapi.foundation"],
        required_backend_ids=["python.fastapi.foundation"],
    )

    multi_engine = CompilerAwareMultiCandidateEngine(
        base_engine=base_engine,
        compiler_gateway=gateway,
        policy=policy,
    )

    proposal = base_engine.propose(proposal_request(), "tester")

    multi_engine.generate_candidates(
        proposal.id,
        GenerateCandidatesRequest(
            mutations=[],
            include_base_mutation=True,
        ),
        "tester",
    )

    evaluations = multi_engine.evaluate_candidates(
        proposal.id,
        "tester",
    )

    assert len(evaluations) == 1

    evaluation = evaluations[0]

    assert evaluation.feasible is False
    assert "compiler_fitness_failed" in evaluation.reasons
