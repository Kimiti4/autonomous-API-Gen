"""
Tests for Phase 21.3 production feedback fitness integration.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from evolution.engine import EvolutionPolicy, SelfEvolutionEngine
from evolution.feedback import (
    FeedbackEvaluationContext,
    FeedbackFitnessEvaluator,
    FeedbackFitnessPolicy,
    FeedbackSeverity,
    FeedbackSignalType,
    InMemorySignalStore,
    ProductionSignal,
)
from evolution.feedback_api import router as feedback_router
from evolution.feedback_engine import ProductionFeedbackAwareEngine
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
from evolution.multi import MultiCandidateEvolutionEngine


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
        title="Production feedback evolution test",
        description="Evaluate candidate architectures with production feedback.",
        target_type=EvolutionTargetType.APPLICATION_ARCHITECTURE,
        target_ref="billing_system",
        base_isr=base_isr(),
        mutation=base_mutation_spec(),
        high_impact=False,
        allow_breaking_changes=False,
        environment="development",
    )


def make_candidate(candidate_id: str = "candidate_feedback_1") -> CandidateArchitecture:
    return CandidateArchitecture(
        id=candidate_id,
        proposal_id="proposal_feedback_1",
        mutation_spec_id="mutation_feedback_1",
        base_isr_hash="sha256:base",
        content_hash="sha256:candidate",
        isr=base_isr(),
        created_at=utcnow().isoformat(),
    )


def build_feedback_wrapper():
    base_engine = SelfEvolutionEngine(
        governance_client=StaticGovernanceClient(
            decision="ALLOW",
            reason="Static governance decision.",
        ),
        policy=EvolutionPolicy(),
    )

    inner_engine = MultiCandidateEvolutionEngine(base_engine)

    store = InMemorySignalStore()

    policy = FeedbackFitnessPolicy(
        require_feedback_evidence=False,
        recommendation_threshold=0.65,
    )

    wrapper = ProductionFeedbackAwareEngine(
        inner_engine=inner_engine,
        signal_store=store,
        policy=policy,
    )

    return base_engine, wrapper


def test_feedback_evaluator_detects_critical_incident():
    store = InMemorySignalStore()

    policy = FeedbackFitnessPolicy(
        require_feedback_evidence=False,
        recommendation_threshold=0.70,
    )

    evaluator = FeedbackFitnessEvaluator(store, policy)

    store.add_signal(
        ProductionSignal(
            signal_type=FeedbackSignalType.INCIDENT,
            severity=FeedbackSeverity.CRITICAL,
            source_id="incident_1",
            source_system="incident_manager",
            service_refs=["BillingService"],
            description="Billing service outage.",
        )
    )

    report = evaluator.evaluate_candidate(
        make_candidate(),
        FeedbackEvaluationContext(target_ref="billing_system"),
    )

    assert report.passed is False
    assert report.matched_signal_count == 1
    assert report.constraints["no_critical_incidents"] is False
    assert report.objectives["reliability"] < policy.default_objective_value
    assert report.recommendations


def test_feedback_evaluator_passes_with_no_signals():
    store = InMemorySignalStore()

    policy = FeedbackFitnessPolicy(
        require_feedback_evidence=False,
    )

    evaluator = FeedbackFitnessEvaluator(store, policy)

    report = evaluator.evaluate_candidate(
        make_candidate(),
        FeedbackEvaluationContext(target_ref="billing_system"),
    )

    assert report.passed is True
    assert report.matched_signal_count == 0
    assert report.objectives["reliability"] == policy.default_objective_value


def test_feedback_aware_engine_marks_candidate_infeasible():
    base_engine, wrapper = build_feedback_wrapper()

    proposal = base_engine.propose(proposal_request(), "tester")

    wrapper.generate_candidates(
        proposal.id,
        GenerateCandidatesRequest(
            mutations=[],
            include_base_mutation=True,
        ),
        "tester",
    )

    wrapper.add_signal(
        ProductionSignal(
            signal_type=FeedbackSignalType.INCIDENT,
            severity=FeedbackSeverity.CRITICAL,
            source_id="incident_2",
            source_system="incident_manager",
            service_refs=["BillingService"],
            description="Billing service outage.",
        )
    )

    evaluations = wrapper.evaluate_candidates(
        proposal.id,
        "tester",
    )

    assert len(evaluations) == 1

    evaluation = evaluations[0]

    assert evaluation.feasible is False
    assert "feedback_fitness_failed" in evaluation.reasons
    assert evaluation.fitness.objectives["feedback_reliability"] < 0.7


def test_feedback_api_signal_ingestion():
    base_engine, wrapper = build_feedback_wrapper()

    app = FastAPI()

    app.state.feedback_engine = wrapper
    app.state.feedback_signal_store = wrapper.signal_store

    app.include_router(feedback_router)

    client = TestClient(app)

    signal_payload = {
        "signal_type": "PERFORMANCE_OBSERVATION",
        "severity": "HIGH",
        "source_id": "latency_observation_1",
        "source_system": "observability_platform",
        "service_refs": ["BillingService"],
        "metric_name": "p95_latency_ms",
        "value": 1800.0,
        "unit": "ms",
        "description": "High latency observed.",
    }

    add_response = client.post(
        "/v1/evolution/feedback/signals",
        json=signal_payload,
    )

    assert add_response.status_code == 201

    list_response = client.get("/v1/evolution/feedback/signals")

    assert list_response.status_code == 200

    signals = list_response.json()

    assert len(signals) == 1
    assert signals[0]["source_id"] == "latency_observation_1"
