"""
Feedback-driven evolution orchestration.

This orchestrator coordinates:
- genome refinement
- targeted mutation generation
- proposal creation
- multi-candidate generation
- candidate evaluation
- Pareto selection
- governance submission
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from .feedback import GenomeRefinementRecommendation
from .genome import (
    ArchitecturalGenome,
    GenomeRefinementEngine,
    GenomeRefinementPolicy,
    create_default_genome,
)
from .genome_mutations import TargetedMutationGenerator
from .models import (
    EvolutionProposalRequest,
    EvolutionTargetType,
    GenerateCandidatesRequest,
    ParetoSelectionPolicy,
    ParetoSelectionResult,
    ProposalStatus,
    utcnow,
)
from .utils import deterministic_id


class EvolutionCampaignRequest(BaseModel):
    """Request to create an evolution campaign."""

    name: str
    description: str = ""

    target_ref: str
    target_type: EvolutionTargetType = (
        EvolutionTargetType.APPLICATION_ARCHITECTURE
    )

    base_isr: dict

    feedback_recommendations: list[GenomeRefinementRecommendation] = Field(
        default_factory=list
    )

    initial_genome: Optional[ArchitecturalGenome] = None

    max_mutations_per_generation: int = Field(default=3, ge=1, le=10)

    selection_policy: ParetoSelectionPolicy = Field(
        default_factory=ParetoSelectionPolicy
    )

    high_impact: bool = False
    allow_breaking_changes: bool = False

    auto_submit_for_approval: bool = True


class GenerationResult(BaseModel):
    """Result of one orchestrated generation."""

    generation_index: int

    proposal_id: str
    genome_id: str

    mutation_spec_ids: list[str] = Field(default_factory=list)

    selected_candidate_id: Optional[str] = None
    pareto_result: Optional[ParetoSelectionResult] = None

    status: str
    error: Optional[str] = None

    created_at: str


class EvolutionCampaign(BaseModel):
    """Evolution campaign aggregate."""

    id: str

    name: str
    description: str = ""

    target_ref: str
    target_type: EvolutionTargetType

    base_isr: dict

    genome: ArchitecturalGenome

    feedback_recommendations: list[GenomeRefinementRecommendation] = Field(
        default_factory=list
    )

    max_mutations_per_generation: int = 3

    selection_policy: ParetoSelectionPolicy

    high_impact: bool = False
    allow_breaking_changes: bool = False

    auto_submit_for_approval: bool = True

    status: str = "ACTIVE"

    generations: list[GenerationResult] = Field(default_factory=list)

    created_at: str
    updated_at: str


class RunGenerationRequest(BaseModel):
    """Request to run one generation of a campaign."""

    feedback_recommendations: list[GenomeRefinementRecommendation] = Field(
        default_factory=list
    )


class EvolutionOrchestrator:
    """Coordinates feedback-driven evolution campaigns."""

    def __init__(
        self,
        base_engine,
        candidate_engine,
        refinement_policy: Optional[GenomeRefinementPolicy] = None,
    ) -> None:
        self.base_engine = base_engine
        self.candidate_engine = candidate_engine

        self.refinement_engine = GenomeRefinementEngine()
        self.refinement_policy = refinement_policy or GenomeRefinementPolicy()
        self.mutation_generator = TargetedMutationGenerator()

        self.campaigns: Dict[str, EvolutionCampaign] = {}

    def create_campaign(
        self,
        request: EvolutionCampaignRequest,
        actor_id: str,
    ) -> EvolutionCampaign:
        genome = request.initial_genome or create_default_genome(
            request.target_ref
        )

        created_at = utcnow().isoformat()

        campaign_id = deterministic_id(
            "evolution_campaign",
            {
                "name": request.name,
                "target_ref": request.target_ref,
                "genome_id": genome.id,
                "created_at": created_at,
            },
        )

        campaign = EvolutionCampaign(
            id=campaign_id,
            name=request.name,
            description=request.description,
            target_ref=request.target_ref,
            target_type=request.target_type,
            base_isr=request.base_isr,
            genome=genome,
            feedback_recommendations=request.feedback_recommendations,
            max_mutations_per_generation=request.max_mutations_per_generation,
            selection_policy=request.selection_policy,
            high_impact=request.high_impact,
            allow_breaking_changes=request.allow_breaking_changes,
            auto_submit_for_approval=request.auto_submit_for_approval,
            status="ACTIVE",
            generations=[],
            created_at=created_at,
            updated_at=created_at,
        )

        self.campaigns[campaign_id] = campaign

        self.base_engine.history.record(
            proposal_id=campaign_id,
            event_type="evolution_campaign_created",
            actor_id=actor_id,
            details={
                "campaign_id": campaign_id,
                "target_ref": campaign.target_ref,
                "genome_id": genome.id,
            },
        )

        return campaign

    def run_generation(
        self,
        campaign_id: str,
        actor_id: str,
        feedback_recommendations: Optional[
            List[GenomeRefinementRecommendation]
        ] = None,
    ) -> GenerationResult:
        campaign = self._get_campaign(campaign_id)

        recommendations = (
            feedback_recommendations
            if feedback_recommendations
            else campaign.feedback_recommendations
        )

        refinement_plan, refined_genome = self.refinement_engine.refine(
            genome=campaign.genome,
            recommendations=recommendations,
            policy=self.refinement_policy,
        )

        campaign.genome = refined_genome

        mutation_specs = self.mutation_generator.generate(
            genome=refined_genome,
            max_mutations=campaign.max_mutations_per_generation,
        )

        base_mutation = mutation_specs[0]

        generation_index = len(campaign.generations) + 1

        proposal_request = EvolutionProposalRequest(
            title=f"{campaign.name} - Generation {generation_index}",
            description=(
                campaign.description
                or "Feedback-driven evolution campaign generation."
            ),
            target_type=campaign.target_type,
            target_ref=campaign.target_ref,
            base_isr=campaign.base_isr,
            mutation=base_mutation,
            high_impact=campaign.high_impact,
            allow_breaking_changes=campaign.allow_breaking_changes,
            environment="development",
        )

        proposal = self.base_engine.propose(proposal_request, actor_id)

        candidate_request = GenerateCandidatesRequest(
            mutations=mutation_specs[1:],
            include_base_mutation=True,
        )

        self.candidate_engine.generate_candidates(
            proposal.id,
            candidate_request,
            actor_id,
        )

        self.candidate_engine.evaluate_candidates(
            proposal.id,
            actor_id,
        )

        pareto_result = self.candidate_engine.select_pareto(
            proposal.id,
            campaign.selection_policy,
            actor_id,
        )

        refreshed_proposal = self.base_engine._get_proposal(proposal.id)

        if (
            campaign.auto_submit_for_approval
            and refreshed_proposal.status == ProposalStatus.EVALUATED
        ):
            refreshed_proposal = self.base_engine.submit_for_approval(
                proposal.id,
                actor_id,
            )

        generation = GenerationResult(
            generation_index=generation_index,
            proposal_id=proposal.id,
            genome_id=refined_genome.id,
            mutation_spec_ids=[
                spec.id or "pending_mutation_id"
                for spec in mutation_specs
            ],
            selected_candidate_id=pareto_result.selected_candidate_id,
            pareto_result=pareto_result,
            status=refreshed_proposal.status.value,
            error=refreshed_proposal.error,
            created_at=utcnow().isoformat(),
        )

        campaign.generations.append(generation)
        campaign.updated_at = utcnow().isoformat()

        self.base_engine.history.record(
            proposal_id=proposal.id,
            event_type="evolution_generation_completed",
            actor_id=actor_id,
            details={
                "campaign_id": campaign_id,
                "generation_index": generation_index,
                "genome_id": refined_genome.id,
                "selected_candidate_id": pareto_result.selected_candidate_id,
                "status": refreshed_proposal.status.value,
            },
        )

        return generation

    def get_campaign(self, campaign_id: str) -> EvolutionCampaign:
        return self._get_campaign(campaign_id)

    def _get_campaign(self, campaign_id: str) -> EvolutionCampaign:
        campaign = self.campaigns.get(campaign_id)

        if not campaign:
            raise KeyError(f"Evolution campaign not found: {campaign_id}")

        return campaign
