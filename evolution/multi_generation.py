"""
Multi-generation evolution campaign engine.

This engine coordinates multiple evolution generations and records
evolutionary memory.
"""

from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field

from .feedback import GenomeRefinementRecommendation
from .memory import (
    EliteRecord,
    GenerationSummary,
    InMemoryEvolutionaryMemory,
)
from .models import utcnow
from .utils import deterministic_id


class CampaignStopPolicy(BaseModel):
    """Policy controlling when a campaign should stop."""

    max_generations: int = Field(default=2, ge=1, le=50)

    require_feasible_candidate: bool = True

    min_objective_improvement: float = Field(default=0.0, le=1.0)

    stagnation_limit: int = Field(default=0, ge=0)

    carry_forward_selected_candidate: bool = True


class RunCampaignRequest(BaseModel):
    """Request to run a multi-generation campaign."""

    feedback_recommendations: List[GenomeRefinementRecommendation] = Field(
        default_factory=list
    )

    stop_policy: Optional[CampaignStopPolicy] = None


class CampaignRunResult(BaseModel):
    """Result of a multi-generation campaign run."""

    campaign_id: str

    generations_run: int

    stop_reason: str

    status: str

    summaries: List[GenerationSummary] = Field(default_factory=list)

    elite_count: int = 0

    completed_at: str


class MultiGenerationCampaignEngine:
    """Coordinates multi-generation evolution campaigns."""

    def __init__(
        self,
        orchestrator,
        memory: Optional[InMemoryEvolutionaryMemory] = None,
        stop_policy: Optional[CampaignStopPolicy] = None,
    ) -> None:
        self.orchestrator = orchestrator
        self.memory = memory or InMemoryEvolutionaryMemory()
        self.stop_policy = stop_policy or CampaignStopPolicy()

    def run_campaign(
        self,
        campaign_id: str,
        actor_id: str,
        feedback_recommendations: Optional[
            List[GenomeRefinementRecommendation]
        ] = None,
        stop_policy: Optional[CampaignStopPolicy] = None,
    ) -> CampaignRunResult:
        policy = stop_policy or self.stop_policy

        campaign = self.orchestrator.get_campaign(campaign_id)

        summaries: List[GenerationSummary] = []

        stop_reason: Optional[str] = None

        previous_diagnostic: Optional[float] = None
        stagnation_count = 0

        for _ in range(policy.max_generations):
            generation_index = len(campaign.generations) + 1

            try:
                generation = self.orchestrator.run_generation(
                    campaign_id=campaign_id,
                    actor_id=actor_id,
                    feedback_recommendations=feedback_recommendations,
                )
            except Exception as exc:
                stop_reason = f"generation_failed: {exc}"
                campaign.status = "FAILED"
                campaign.updated_at = utcnow().isoformat()
                break

            summary = self._record_generation(
                campaign=campaign,
                generation=generation,
                actor_id=actor_id,
            )

            summaries.append(summary)

            if (
                policy.carry_forward_selected_candidate
                and generation.selected_candidate_id
            ):
                candidate = self.orchestrator.base_engine.candidates.get(
                    generation.selected_candidate_id
                )

                if candidate:
                    campaign.base_isr = candidate.isr

            if (
                generation.selected_candidate_id is None
                and policy.require_feasible_candidate
            ):
                stop_reason = "no_feasible_candidate"
                campaign.status = "FAILED"
                campaign.updated_at = utcnow().isoformat()
                break

            diagnostic = self._diagnostic_score(
                summary.objectives,
                summary.constraints,
            )

            if policy.stagnation_limit > 0 and previous_diagnostic is not None:
                improvement = diagnostic - previous_diagnostic

                if improvement < policy.min_objective_improvement:
                    stagnation_count += 1
                else:
                    stagnation_count = 0

                if stagnation_count >= policy.stagnation_limit:
                    stop_reason = "stagnation"
                    break

            previous_diagnostic = diagnostic

        if stop_reason is None:
            stop_reason = "max_generations_reached"

        if campaign.status != "FAILED":
            campaign.status = "COMPLETED"

        campaign.updated_at = utcnow().isoformat()

        elite_count = len(self.memory.list_elites(campaign.id))

        result = CampaignRunResult(
            campaign_id=campaign.id,
            generations_run=len(summaries),
            stop_reason=stop_reason,
            status=campaign.status,
            summaries=summaries,
            elite_count=elite_count,
            completed_at=utcnow().isoformat(),
        )

        self.orchestrator.base_engine.history.record(
            proposal_id=campaign.id,
            event_type="multi_generation_campaign_completed",
            actor_id=actor_id,
            details={
                "campaign_id": campaign.id,
                "generations_run": len(summaries),
                "stop_reason": stop_reason,
                "status": campaign.status,
                "elite_count": elite_count,
            },
        )

        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _record_generation(
        self,
        campaign,
        generation,
        actor_id: str,
    ) -> GenerationSummary:
        evaluation = self._get_selected_evaluation(generation)

        objectives: dict[str, float] = {}
        constraints: dict[str, bool] = {}

        feasible = False

        if evaluation and evaluation.fitness:
            objectives = dict(evaluation.fitness.objectives)
            constraints = dict(evaluation.fitness.constraints)

        if evaluation:
            feasible = bool(getattr(evaluation, "feasible", False))

        summary_id = deterministic_id(
            "generation_summary",
            {
                "campaign_id": campaign.id,
                "generation_index": generation.generation_index,
                "proposal_id": generation.proposal_id,
            },
        )

        summary = GenerationSummary(
            id=summary_id,
            campaign_id=campaign.id,
            generation_index=generation.generation_index,
            proposal_id=generation.proposal_id,
            genome_id=generation.genome_id,
            selected_candidate_id=generation.selected_candidate_id,
            status=generation.status,
            objectives=objectives,
            constraints=constraints,
            elite_count=len(self.memory.list_elites(campaign.id)),
            created_at=utcnow().isoformat()
        )

        self.memory.save_generation_summary(summary)

        if feasible and generation.selected_candidate_id:
            candidate = self.orchestrator.base_engine.candidates.get(
                generation.selected_candidate_id
            )

            if candidate:
                elite_id = deterministic_id(
                    "elite_candidate",
                    {
                        "campaign_id": campaign.id,
                        "candidate_id": candidate.id,
                        "content_hash": candidate.content_hash,
                    },
                )

                elite = EliteRecord(
                    id=elite_id,
                    campaign_id=campaign.id,
                    generation_index=generation.generation_index,
                    proposal_id=generation.proposal_id,
                    candidate_id=candidate.id,
                    genome_id=generation.genome_id,
                    isr_content_hash=candidate.content_hash,
                    objectives=objectives,
                    constraints=constraints,
                    created_at=utcnow().isoformat()
                )

                self.memory.save_elite(elite)

        return summary

    def _get_selected_evaluation(self, generation):
        if not generation.selected_candidate_id:
            return None

        candidate_engine = self.orchestrator.candidate_engine

        if hasattr(candidate_engine, "get_evaluations"):
            evaluations = candidate_engine.get_evaluations(generation.proposal_id)
        else:
            evaluations = list(
                getattr(candidate_engine, "evaluations", {})
                .get(generation.proposal_id, {})
                .values()
            )

        for evaluation in evaluations:
            if evaluation.candidate_id == generation.selected_candidate_id:
                return evaluation

        return None

    def _diagnostic_score(
        self,
        objectives: dict[str, float],
        constraints: dict[str, bool],
    ) -> float:
        """
        Produce a diagnostic progress score.

        This score is used only for campaign stopping diagnostics.
        It is not used for Pareto selection.
        """

        values = [
            float(value)
            for value in objectives.values()
            if isinstance(value, (int, float))
        ]

        if not values:
            return 0.0

        base_score = sum(values) / len(values)

        if constraints:
            passed_constraints = sum(
                1
                for value in constraints.values()
                if bool(value)
            )

            constraint_ratio = passed_constraints / len(constraints)

            base_score *= constraint_ratio

        return round(base_score, 6)
