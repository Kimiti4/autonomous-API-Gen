"""
Tests for Phase 21.4 feedback-driven genome refinement and orchestration.
"""

from evolution.engine import EvolutionPolicy, SelfEvolutionEngine
from evolution.feedback import GenomeRefinementRecommendation
from evolution.governance import StaticGovernanceClient
from evolution.genome import (
    ChromosomeFamily,
    GenomeRefinementEngine,
    GenomeRefinementPolicy,
    create_default_genome,
)
from evolution.genome_mutations import TargetedMutationGenerator
from evolution.models import EvolutionTargetType, ParetoSelectionPolicy
from evolution.multi import MultiCandidateEvolutionEngine
from evolution.mutation import MutationEngine
from evolution.orchestration import (
    EvolutionCampaignRequest,
    EvolutionOrchestrator,
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


def reliability_recommendation() -> GenomeRefinementRecommendation:
    return GenomeRefinementRecommendation(
        id="recommendation_reliability_1",
        objective="reliability",
        chromosome_family=ChromosomeFamily.RELIABILITY.value,
        gene_id="reliability_gene",
        action="STRENGTHEN",
        rationale="Production incidents indicate weak reliability.",
        target_refs=["billing_system"],
        signal_ids=["signal_1"],
        evidence_refs=["signal_1"],
    )


def test_genome_refinement_increases_priority():
    genome = create_default_genome("billing_system")

    engine = GenomeRefinementEngine()
    policy = GenomeRefinementPolicy(priority_increment=0.2)

    old_gene = next(
        gene
        for gene in genome.genes
        if gene.gene_id == "reliability_gene"
    )

    plan, refined_genome = engine.refine(
        genome=genome,
        recommendations=[reliability_recommendation()],
        policy=policy,
    )

    new_gene = next(
        gene
        for gene in refined_genome.genes
        if gene.gene_id == "reliability_gene"
    )

    assert plan.updates
    assert new_gene.priority > old_gene.priority
    assert refined_genome.version == genome.version + 1


def test_targeted_mutation_generator_creates_reliability_mutation():
    genome = create_default_genome("billing_system")

    engine = GenomeRefinementEngine()
    policy = GenomeRefinementPolicy(priority_increment=0.3)

    _, refined_genome = engine.refine(
        genome=genome,
        recommendations=[reliability_recommendation()],
        policy=policy,
    )

    generator = TargetedMutationGenerator()

    mutations = generator.generate(refined_genome, max_mutations=3)

    assert mutations

    chromosome_families = {
        mutation.chromosome_family
        for mutation in mutations
    }

    assert ChromosomeFamily.RELIABILITY.value in chromosome_families

    mutation_engine = MutationEngine()

    mutated_isr = mutation_engine.apply(base_isr(), mutations[0])

    assert mutated_isr["reliability"]["retry_policy"] == "enabled"
    assert mutated_isr["reliability"]["circuit_breaker"] is True


def test_orchestrator_runs_feedback_driven_generation():
    base_engine = SelfEvolutionEngine(
        governance_client=StaticGovernanceClient(
            decision="ALLOW",
            reason="Static governance decision.",
        ),
        policy=EvolutionPolicy(),
    )

    candidate_engine = MultiCandidateEvolutionEngine(base_engine)

    orchestrator = EvolutionOrchestrator(
        base_engine=base_engine,
        candidate_engine=candidate_engine,
    )

    campaign_request = EvolutionCampaignRequest(
        name="Billing reliability evolution",
        description="Improve billing reliability using production feedback.",
        target_ref="billing_system",
        target_type=EvolutionTargetType.APPLICATION_ARCHITECTURE,
        base_isr=base_isr(),
        feedback_recommendations=[reliability_recommendation()],
        max_mutations_per_generation=2,
        selection_policy=ParetoSelectionPolicy(max_selected=1),
        auto_submit_for_approval=True,
    )

    campaign = orchestrator.create_campaign(campaign_request, "tester")

    generation = orchestrator.run_generation(
        campaign.id,
        "tester",
    )

    assert generation.generation_index == 1
    assert generation.selected_candidate_id is not None
    assert generation.status in {
        "APPROVED",
        "PENDING_APPROVAL",
        "EVALUATED",
    }
