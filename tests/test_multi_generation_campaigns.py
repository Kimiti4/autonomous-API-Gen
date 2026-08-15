"""
Tests for Phase 21.5 multi-generation campaigns and evolutionary memory.
"""

from evolution.engine import EvolutionPolicy, SelfEvolutionEngine
from evolution.feedback import GenomeRefinementRecommendation
from evolution.governance import StaticGovernanceClient
from evolution.memory import InMemoryEvolutionaryMemory
from evolution.models import EvolutionTargetType, ParetoSelectionPolicy
from evolution.multi import MultiCandidateEvolutionEngine
from evolution.multi_generation import (
    CampaignStopPolicy,
    MultiGenerationCampaignEngine,
)
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
        chromosome_family="Reliability",
        gene_id="reliability_gene",
        action="STRENGTHEN",
        rationale="Production incidents indicate weak reliability.",
        target_refs=["billing_system"],
        signal_ids=["signal_1"],
        evidence_refs=["signal_1"],
    )


def build_stack():
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

    memory = InMemoryEvolutionaryMemory()

    stop_policy = CampaignStopPolicy(
        max_generations=2,
        require_feasible_candidate=True,
        carry_forward_selected_candidate=True,
    )

    multi_generation_engine = MultiGenerationCampaignEngine(
        orchestrator=orchestrator,
        memory=memory,
        stop_policy=stop_policy,
    )

    return orchestrator, multi_generation_engine, memory


def test_multi_generation_campaign_runs_and_records_memory():
    orchestrator, multi_generation_engine, memory = build_stack()

    campaign_request = EvolutionCampaignRequest(
        name="Billing reliability evolution",
        description="Multi-generation reliability improvement campaign.",
        target_ref="billing_system",
        target_type=EvolutionTargetType.APPLICATION_ARCHITECTURE,
        base_isr=base_isr(),
        feedback_recommendations=[reliability_recommendation()],
        max_mutations_per_generation=2,
        selection_policy=ParetoSelectionPolicy(max_selected=1),
        auto_submit_for_approval=True,
    )

    campaign = orchestrator.create_campaign(campaign_request, "tester")

    result = multi_generation_engine.run_campaign(
        campaign.id,
        "tester",
    )

    assert result.generations_run == 2
    assert result.stop_reason == "max_generations_reached"
    assert result.status == "COMPLETED"

    summaries = memory.list_generation_summaries(campaign.id)

    assert len(summaries) == 2

    elites = memory.list_elites(campaign.id)

    assert len(elites) >= 1

    trend = memory.get_trend(campaign.id)

    assert trend.generation_count == 2
    assert trend.elite_count >= 1


def test_campaign_carries_forward_selected_candidate():
    orchestrator, multi_generation_engine, memory = build_stack()

    campaign_request = EvolutionCampaignRequest(
        name="Billing carry-forward evolution",
        description="Verify selected candidate becomes next base ISR.",
        target_ref="billing_system",
        target_type=EvolutionTargetType.APPLICATION_ARCHITECTURE,
        base_isr=base_isr(),
        feedback_recommendations=[reliability_recommendation()],
        max_mutations_per_generation=1,
        selection_policy=ParetoSelectionPolicy(max_selected=1),
        auto_submit_for_approval=False,
    )

    campaign = orchestrator.create_campaign(campaign_request, "tester")

    original_isr_hash_fields = {
        "isr_id": campaign.base_isr.get("isr_id"),
        "version": campaign.base_isr.get("version"),
    }

    multi_generation_engine.run_campaign(
        campaign.id,
        "tester",
    )

    refreshed_campaign = orchestrator.get_campaign(campaign.id)

    evolved_isr = refreshed_campaign.base_isr

    assert evolved_isr is not None

    assert evolved_isr.get("isr_id") == original_isr_hash_fields["isr_id"]

    assert "evolution" in evolved_isr

    assert evolved_isr["evolution"].get("mutations")
