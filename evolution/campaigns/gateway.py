"""
Candidate generation and fitness evaluation gateways.
"""

from __future__ import annotations

from typing import List, Protocol

from .models import CandidateFitness, EvolutionCampaign, EvolutionCandidate


class CandidateGenerator(Protocol):
    """Generates candidate architectures for a campaign generation."""

    def generate_candidates(
        self,
        campaign: EvolutionCampaign,
        generation_index: int,
    ) -> List[EvolutionCandidate]:
        ...


class FitnessGateway(Protocol):
    """Evaluates candidate fitness."""

    def evaluate_candidate(
        self,
        candidate: EvolutionCandidate,
        campaign: EvolutionCampaign,
    ) -> CandidateFitness:
        ...


class DeterministicCandidateGenerator:
    """Deterministic candidate generator for tests and local development."""

    def generate_candidates(
        self,
        campaign: EvolutionCampaign,
        generation_index: int,
    ) -> List[EvolutionCandidate]:
        candidates: List[EvolutionCandidate] = []

        for index in range(campaign.population_size):
            candidate_id = (
                f"candidate:{campaign.id}:g{generation_index}:{index}"
            )

            candidates.append(
                EvolutionCandidate(
                    id=candidate_id,
                    campaign_id=campaign.id,
                    generation_index=generation_index,
                    genome_ref=campaign.genome_ref,
                    metadata={
                        "generation_index": generation_index,
                        "candidate_index": index,
                    },
                )
            )

        return candidates


class StaticFitnessGateway:
    """Static fitness gateway for tests and local development."""

    def evaluate_candidate(
        self,
        candidate: EvolutionCandidate,
        campaign: EvolutionCampaign,
    ) -> CandidateFitness:
        return CandidateFitness(
            candidate_id=candidate.id,
            objectives={
                "maintainability": 0.7,
                "reliability": 0.7,
                "security": 0.7,
                "performance": 0.7,
                "cost_efficiency": 0.7,
            },
            constraints={
                "architecture_valid": True,
                "security_review_passed": True,
            },
            passed=True,
        )
