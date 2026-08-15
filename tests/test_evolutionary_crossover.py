"""
Tests for Phase 21.6 evolutionary crossover, recombination, and diversity.
"""

from evolution.engine import EvolutionPolicy, SelfEvolutionEngine
from evolution.governance import StaticGovernanceClient
from evolution.models import (
    EvolutionProposalRequest,
    EvolutionTargetType,
    MutationOperationSpec,
    MutationOperationType,
    MutationSpec,
)
from evolution.population import PopulationDiversityController
from evolution.recombination import (
    RecombinationContext,
    RecombinationEngine,
    RecombinationPolicy,
    register_offspring_candidate,
)


def parent_a_isr() -> dict:
    return {
        "isr_id": "parent_a",
        "version": "1.0.0",
        "name": "Parent A",
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
                    }
                ],
            }
        ],
        "reliability": {
            "retry_policy": "enabled",
        },
        "security": {
            "authentication": "OIDC",
        },
        "testing": {
            "unit_tests": True,
        },
        "deployment": {
            "canary": True,
        },
    }


def parent_b_isr() -> dict:
    return {
        "isr_id": "parent_b",
        "version": "1.0.0",
        "name": "Parent B",
        "domains": [
            {
                "name": "payments",
                "services": [
                    {
                        "name": "PaymentService",
                        "apis": [
                            {
                                "name": "authorizePayment"
                            }
                        ],
                    }
                ],
            }
        ],
        "performance": {
            "caching": "enabled",
        },
        "observability": {
            "metrics": True,
        },
        "testing": {
            "contract_tests": True,
        },
        "deployment": {
            "blue_green": True,
        },
    }


def test_policy_block_crossover_combines_strengths():
    engine = RecombinationEngine()

    context = RecombinationContext(
        parent_candidate_ids=["parent_a", "parent_b"],
        objectives_by_parent={
            "parent_a": {
                "feedback_reliability": 0.9,
                "feedback_security_posture": 0.85,
                "testability": 0.4,
                "deployment_readiness": 0.4,
            },
            "parent_b": {
                "feedback_performance_efficiency": 0.9,
                "feedback_operational_stability": 0.9,
                "testability": 0.7,
                "deployment_readiness": 0.7,
            },
        },
    )

    result = engine.recombine_candidates(
        parent_a=parent_a_isr(),
        parent_b=parent_b_isr(),
        policy=RecombinationPolicy(
            operator="policy_block",
            max_offspring=2,
        ),
        context=context,
    )

    assert len(result.offspring) == 2

    child_one = result.offspring[0].isr
    child_two = result.offspring[1].isr

    assert child_one["reliability"] == parent_a_isr()["reliability"]
    assert child_one["performance"] == parent_b_isr()["performance"]

    assert child_one["testing"] == parent_b_isr()["testing"]
    assert child_two["testing"] == parent_a_isr()["testing"]

    assert child_one["evolution"]["crossovers"]
    assert child_two["evolution"]["crossovers"]


def test_domain_crossover_merges_domains():
    engine = RecombinationEngine()

    result = engine.recombine_candidates(
        parent_a=parent_a_isr(),
        parent_b=parent_b_isr(),
        policy=RecombinationPolicy(
            operator="domain",
            max_offspring=2,
        ),
        context=RecombinationContext(
            parent_candidate_ids=["parent_a", "parent_b"],
        ),
    )

    child_one = result.offspring[0].isr

    domain_names = {
        domain["name"]
        for domain in child_one["domains"]
    }

    assert "billing" in domain_names
    assert "payments" in domain_names


def test_population_features_and_diversity():
    controller = PopulationDiversityController()

    isr_one = parent_a_isr()
    isr_two = parent_a_isr()
    isr_three = parent_b_isr()

    controller.register_candidate("candidate_one", isr_one)
    controller.register_candidate("candidate_two", isr_two)
    controller.register_candidate("candidate_three", isr_three)

    assert controller.similarity("candidate_one", "candidate_two") > 0.9

    selected = controller.select_diverse(
        candidate_ids=[
            "candidate_one",
            "candidate_two",
            "candidate_three",
        ],
        max_select=2,
    )

    assert len(selected) == 2
    assert "candidate_three" in selected


def test_register_offspring_candidate():
    base_engine = SelfEvolutionEngine(
        governance_client=StaticGovernanceClient(
            decision="ALLOW",
            reason="Static governance decision.",
        ),
        policy=EvolutionPolicy(),
    )

    proposal_request = EvolutionProposalRequest(
        title="Recombination proposal",
        description="Proposal used to register recombined offspring.",
        target_type=EvolutionTargetType.APPLICATION_ARCHITECTURE,
        target_ref="billing_system",
        base_isr=parent_a_isr(),
        mutation=MutationSpec(
            id="base_mutation",
            operator="test_mutator",
            chromosome_family="Architecture",
            gene_id="architecture_gene",
            rationale="Base mutation.",
            operations=[
                MutationOperationSpec(
                    operation=MutationOperationType.MERGE_OBJECT,
                    path="architecture",
                    value={
                        "modularity": True,
                    },
                )
            ],
        ),
    )

    proposal = base_engine.propose(proposal_request, "tester")

    engine = RecombinationEngine()

    result = engine.recombine_candidates(
        parent_a=parent_a_isr(),
        parent_b=parent_b_isr(),
        policy=RecombinationPolicy(
            operator="domain",
            max_offspring=1,
        ),
        context=RecombinationContext(
            parent_candidate_ids=["parent_a", "parent_b"],
        ),
    )

    offspring = result.offspring[0]

    candidate = register_offspring_candidate(
        base_engine=base_engine,
        proposal_id=proposal.id,
        offspring=offspring,
    )

    refreshed = base_engine._get_proposal(proposal.id)

    assert candidate.id in refreshed.candidate_ids
    assert candidate.id in base_engine.candidates
