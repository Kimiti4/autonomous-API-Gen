"""
Tests for Phase 21.5 multi-generation evolution campaigns.
"""

from evolution.campaigns.engine import MultiGenerationCampaignEngine
from evolution.campaigns.gateway import (
    DeterministicCandidateGenerator,
    StaticFitnessGateway,
)
from evolution.campaigns.models import (
    CandidateFitness,
    EvolutionCampaign,
    EvolutionCandidate,
    StopPolicy,
)


class IncreasingFitnessGateway:
    def evaluate_candidate(
        self,
        candidate: EvolutionCandidate,
        campaign: EvolutionCampaign,
    ) -> CandidateFitness:
        generation_index = candidate.generation_index

        base = 0.5 + (0.1 * generation_index)

        return CandidateFitness(
            candidate_id=candidate.id,
            objectives={
                "reliability": min(0.95, base),
                "performance": min(0.95, base + 0.02),
                "cost_efficiency": min(0.95, base - 0.02),
            },
            constraints={
                "architecture_valid": True,
            },
            passed=True,
        )


def test_multi_generation_campaign_completes():
    engine = MultiGenerationCampaignEngine(
        candidate_generator=DeterministicCandidateGenerator(),
        fitness_gateway=IncreasingFitnessGateway(),
    )

    campaign = engine.create_campaign(
        name="Improve billing reliability",
        objective="Improve reliability of billing architecture.",
        population_size=4,
        stop_policy=StopPolicy(max_generations=3),
    )

    completed = engine.run_campaign(campaign.id)

    assert completed.status == "COMPLETED"
    assert len(completed.generations) == 3
    assert completed.elites

    report = engine.campaign_report(campaign.id)

    assert report.generation_count == 3
    assert report.elite_count > 0
    assert report.best_objectives


def test_stagnation_stops_campaign():
    engine = MultiGenerationCampaignEngine(
        candidate_generator=DeterministicCandidateGenerator(),
        fitness_gateway=StaticFitnessGateway(),
    )

    campaign = engine.create_campaign(
        name="Stagnation campaign",
        objective="Detect stagnation.",
        population_size=3,
        stop_policy=StopPolicy(
            max_generations=10,
            stagnation_generations=2,
        ),
    )

    completed = engine.run_campaign(campaign.id)

    assert completed.status == "COMPLETED"
    assert len(completed.generations) < 10


def test_campaign_memory_records_generations():
    engine = MultiGenerationCampaignEngine(
        candidate_generator=DeterministicCandidateGenerator(),
        fitness_gateway=IncreasingFitnessGateway(),
    )

    campaign = engine.create_campaign(
        name="Memory campaign",
        objective="Preserve evolutionary memory.",
        population_size=2,
        stop_policy=StopPolicy(max_generations=2),
    )

    engine.run_campaign(campaign.id)

    records = engine.campaign_memory(campaign.id)

    record_types = {record.record_type for record in records}

    assert "campaign_created" in record_types
    assert "generation_completed" in record_types
