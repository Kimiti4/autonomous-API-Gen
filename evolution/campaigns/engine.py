"""
Multi-generation evolution campaign engine.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from ..utils import deterministic_id, utcnow
from .gateway import CandidateGenerator, FitnessGateway
from .memory import EvolutionaryMemory
from .models import (
    CandidateFitness,
    CampaignReport,
    EliteRecord,
    EvolutionCampaign,
    EvolutionCandidate,
    GenerationRecord,
    StopPolicy,
)
from .selection import select_pareto_front


class MultiGenerationCampaignEngine:
    """Coordinates multi-generation evolution campaigns."""

    def __init__(
        self,
        candidate_generator: CandidateGenerator,
        fitness_gateway: FitnessGateway,
        memory: EvolutionaryMemory | None = None,
    ) -> None:
        self.candidate_generator = candidate_generator
        self.fitness_gateway = fitness_gateway
        self.memory = memory or EvolutionaryMemory()

        self.campaigns: Dict[str, EvolutionCampaign] = {}

    # ------------------------------------------------------------------
    # Campaign lifecycle
    # ------------------------------------------------------------------

    def create_campaign(
        self,
        name: str,
        objective: str,
        population_size: int = 5,
        genome_ref: Optional[str] = None,
        stop_policy: StopPolicy | None = None,
    ) -> EvolutionCampaign:
        campaign_id = deterministic_id(
            "evolution_campaign",
            {
                "name": name,
                "objective": objective,
                "created_at": utcnow().isoformat(),
            },
        )

        campaign = EvolutionCampaign(
            id=campaign_id,
            name=name,
            objective=objective,
            genome_ref=genome_ref,
            population_size=population_size,
            stop_policy=stop_policy or StopPolicy(),
        )

        self.campaigns[campaign_id] = campaign

        self.memory.add_record(
            campaign_id=campaign_id,
            record_type="campaign_created",
            payload={
                "name": name,
                "objective": objective,
                "population_size": population_size,
            },
        )

        return campaign

    def run_generation(self, campaign_id: str) -> GenerationRecord:
        campaign = self._get_campaign(campaign_id)

        if campaign.status not in {"DRAFT", "RUNNING"}:
            raise ValueError("Campaign cannot run generation in current state.")

        campaign.status = "RUNNING"

        generation_index = len(campaign.generations) + 1

        candidates = self.candidate_generator.generate_candidates(
            campaign,
            generation_index,
        )

        if not candidates:
            campaign.status = "FAILED"
            campaign.updated_at = utcnow().isoformat()

            raise ValueError("Candidate generator produced no candidates.")

        fitness_results: Dict[str, CandidateFitness] = {}

        for candidate in candidates:
            fitness_results[candidate.id] = self.fitness_gateway.evaluate_candidate(
                candidate,
                campaign,
            )

        selected_candidate_ids = select_pareto_front(fitness_results)

        best_objectives = self._best_objectives(fitness_results)

        previous_generation = (
            campaign.generations[-1]
            if campaign.generations
            else None
        )

        improvements_count = self._improvements_count(
            previous_generation.best_objectives if previous_generation else {},
            best_objectives,
            campaign.stop_policy.min_improvement,
        )

        stagnation_counter = 0

        if improvements_count == 0:
            stagnation_counter = (
                previous_generation.stagnation_counter + 1
                if previous_generation
                else 1
            )

        elite_candidate_ids = self._update_elites(
            campaign,
            generation_index,
            selected_candidate_ids,
            fitness_results,
            candidates,
        )

        generation = GenerationRecord(
            generation_index=generation_index,
            candidate_ids=[candidate.id for candidate in candidates],
            selected_candidate_ids=selected_candidate_ids,
            elite_candidate_ids=elite_candidate_ids,
            best_objectives=best_objectives,
            improvements_count=improvements_count,
            stagnation_counter=stagnation_counter,
        )

        campaign.generations.append(generation)

        self.memory.add_record(
            campaign_id=campaign.id,
            record_type="generation_completed",
            payload={
                "generation_index": generation_index,
                "candidate_count": len(candidates),
                "selected_candidate_ids": selected_candidate_ids,
                "best_objectives": best_objectives,
                "improvements_count": improvements_count,
                "stagnation_counter": stagnation_counter,
            },
            generation_index=generation_index,
        )

        self._update_campaign_status(campaign)

        campaign.updated_at = utcnow().isoformat()

        return generation

    def run_campaign(
        self,
        campaign_id: str,
        max_generations: Optional[int] = None,
    ) -> EvolutionCampaign:
        campaign = self._get_campaign(campaign_id)

        limit = max_generations or campaign.stop_policy.max_generations

        while len(campaign.generations) < limit:
            if campaign.status not in {"DRAFT", "RUNNING"}:
                break

            self.run_generation(campaign_id)

        return campaign

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def campaign_report(self, campaign_id: str) -> CampaignReport:
        campaign = self._get_campaign(campaign_id)

        best_objectives: Dict[str, float] = {}

        if campaign.generations:
            best_objectives = campaign.generations[-1].best_objectives

        objective_trends: Dict[str, List[float]] = {}

        for generation in campaign.generations:
            for objective, value in generation.best_objectives.items():
                objective_trends.setdefault(objective, []).append(value)

        recommendations: List[str] = []

        if campaign.generations:
            last_generation = campaign.generations[-1]

            if last_generation.stagnation_counter >= 2:
                recommendations.append(
                    "Campaign is stagnating. Consider mutation expansion or genome refinement."
                )

            if not last_generation.selected_candidate_ids:
                recommendations.append(
                    "No Pareto-optimal candidates selected. Review fitness constraints."
                )

        return CampaignReport(
            campaign_id=campaign.id,
            status=campaign.status,
            generation_count=len(campaign.generations),
            elite_count=len(campaign.elites),
            best_objectives=best_objectives,
            objective_trends=objective_trends,
            recommendations=recommendations,
        )

    def campaign_memory(self, campaign_id: str):
        return self.memory.campaign_records(campaign_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_campaign(self, campaign_id: str) -> EvolutionCampaign:
        campaign = self.campaigns.get(campaign_id)

        if not campaign:
            raise KeyError(f"Campaign not found: {campaign_id}")

        return campaign

    def _best_objectives(
        self,
        fitness_results: Dict[str, CandidateFitness],
    ) -> Dict[str, float]:
        best_objectives: Dict[str, float] = {}

        for fitness in fitness_results.values():
            if not fitness.passed:
                continue

            if not all(fitness.constraints.values()):
                continue

            for objective, value in fitness.objectives.items():
                current_best = best_objectives.get(objective)

                if current_best is None or value > current_best:
                    best_objectives[objective] = value

        return best_objectives

    def _improvements_count(
        self,
        previous_objectives: Dict[str, float],
        current_objectives: Dict[str, float],
        min_improvement: float,
    ) -> int:
        if not previous_objectives:
            return len(current_objectives)

        improvements = 0

        for objective, value in current_objectives.items():
            previous_value = previous_objectives.get(objective, 0.0)

            if value > previous_value + min_improvement:
                improvements += 1

        return improvements

    def _update_elites(
        self,
        campaign: EvolutionCampaign,
        generation_index: int,
        selected_candidate_ids: List[str],
        fitness_results: Dict[str, CandidateFitness],
        candidates: List[EvolutionCandidate],
    ) -> List[str]:
        candidates_by_id = {candidate.id: candidate for candidate in candidates}

        elite_candidate_ids: List[str] = []

        existing_elite_ids = {elite.candidate_id for elite in campaign.elites}

        for candidate_id in selected_candidate_ids:
            if candidate_id in existing_elite_ids:
                elite_candidate_ids.append(candidate_id)
                continue

            fitness = fitness_results.get(candidate_id)

            candidate = candidates_by_id.get(candidate_id)

            if not fitness or not candidate:
                continue

            campaign.elites.append(
                EliteRecord(
                    candidate_id=candidate_id,
                    campaign_id=campaign.id,
                    generation_index=generation_index,
                    objectives=fitness.objectives,
                    genome_ref=candidate.genome_ref,
                )
            )

            elite_candidate_ids.append(candidate_id)

        campaign.elites = campaign.elites[-campaign.stop_policy.max_elites :]

        return elite_candidate_ids

    def _update_campaign_status(self, campaign: EvolutionCampaign) -> None:
        stop_policy = campaign.stop_policy

        if len(campaign.generations) >= stop_policy.max_generations:
            campaign.status = "COMPLETED"
            return

        if campaign.generations:
            last_generation = campaign.generations[-1]

            if last_generation.stagnation_counter >= stop_policy.stagnation_generations:
                campaign.status = "COMPLETED"
                return

            reached_targets = all(
                last_generation.best_objectives.get(objective, 0.0) >= target
                for objective, target in stop_policy.target_objectives.items()
            )

            if stop_policy.target_objectives and reached_targets:
                campaign.status = "COMPLETED"
                return

        campaign.status = "RUNNING"
