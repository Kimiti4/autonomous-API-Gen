"""
Architectural genome and feedback-driven genome refinement.

The genome represents architectural decision priorities, not implementation
details.

Feedback recommendations refine genome priorities. Refined genomes guide
targeted mutation generation.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from .feedback import GenomeRefinementRecommendation
from .models import (
    MutationOperationSpec,
    MutationOperationType,
    MutationSpec,
    utcnow,
)
from .utils import deterministic_id


class ChromosomeFamily(str, Enum):
    """Architectural chromosome families."""

    ARCHITECTURE = "Architecture"
    PERSISTENCE = "Persistence"
    INFRASTRUCTURE = "Infrastructure"
    SECURITY = "Security"
    MESSAGING = "Messaging"
    OBSERVABILITY = "Observability"
    AI = "AI"
    TESTING = "Testing"
    DEPLOYMENT = "Deployment"
    FRONTEND = "Frontend"
    BACKEND = "Backend"
    GOVERNANCE = "Governance"
    DOCUMENTATION = "Documentation"
    PERFORMANCE = "Performance"
    RELIABILITY = "Reliability"


OBJECTIVE_TO_CHROMOSOME_FAMILY = {
    "reliability": ChromosomeFamily.RELIABILITY,
    "security_posture": ChromosomeFamily.SECURITY,
    "performance_efficiency": ChromosomeFamily.PERFORMANCE,
    "cost_efficiency": ChromosomeFamily.INFRASTRUCTURE,
    "user_satisfaction": ChromosomeFamily.FRONTEND,
    "operational_stability": ChromosomeFamily.OBSERVABILITY,
}


class GenomeGene(BaseModel):
    """A gene inside the architectural genome."""

    gene_id: str
    chromosome_family: ChromosomeFamily

    description: str = ""

    priority: float = Field(default=0.5, ge=0.0, le=1.0)
    active: bool = True

    tags: list[str] = Field(default_factory=list)


class ArchitecturalGenome(BaseModel):
    """Architectural genome."""

    id: str
    version: int = 1

    base_ref: Optional[str] = None

    genes: list[GenomeGene] = Field(default_factory=list)

    created_at: str


class GenePriorityUpdate(BaseModel):
    """A priority update produced by genome refinement."""

    gene_id: str
    chromosome_family: ChromosomeFamily

    old_priority: float
    new_priority: float
    delta: float

    reason: str = ""


class GenomeRefinementPlan(BaseModel):
    """Plan describing how a genome was refined."""

    id: str
    genome_id: str

    updates: list[GenePriorityUpdate] = Field(default_factory=list)
    new_genes: list[str] = Field(default_factory=list)
    deactivated_genes: list[str] = Field(default_factory=list)

    rationale: str = ""

    created_at: str


class GenomeRefinementPolicy(BaseModel):
    """Policy controlling genome refinement."""

    priority_increment: float = Field(default=0.15, ge=0.0, le=1.0)
    max_priority: float = Field(default=1.0, ge=0.0, le=1.0)
    min_priority: float = Field(default=0.0, ge=0.0, le=1.0)

    default_new_gene_priority: float = Field(default=0.5, ge=0.0, le=1.0)

    create_missing_genes: bool = True


class GenomeRefinementEngine:
    """Refines genomes using feedback recommendations."""

    def refine(
        self,
        genome: ArchitecturalGenome,
        recommendations: List[GenomeRefinementRecommendation],
        policy: Optional[GenomeRefinementPolicy] = None,
    ) -> tuple[GenomeRefinementPlan, ArchitecturalGenome]:
        policy = policy or GenomeRefinementPolicy()

        if not recommendations:
            plan = GenomeRefinementPlan(
                id=deterministic_id(
                    "genome_refinement_plan",
                    {
                        "genome_id": genome.id,
                        "recommendation_count": 0,
                    },
                ),
                genome_id=genome.id,
                updates=[],
                new_genes=[],
                deactivated_genes=[],
                rationale="No feedback recommendations supplied.",
                created_at=utcnow().isoformat(),
            )

            return plan, genome

        genes_by_id: Dict[str, GenomeGene] = {
            gene.gene_id: gene.model_copy(deep=True)
            for gene in genome.genes
        }

        updates: List[GenePriorityUpdate] = []
        new_gene_ids: List[str] = []
        deactivated_gene_ids: List[str] = []

        for recommendation in recommendations:
            chromosome_family = self._resolve_chromosome_family(
                recommendation
            )

            gene_id = (
                recommendation.gene_id
                or f"{chromosome_family.value.lower()}_{recommendation.objective}"
            )

            gene = genes_by_id.get(gene_id)

            if not gene:
                if not policy.create_missing_genes:
                    continue

                gene = GenomeGene(
                    gene_id=gene_id,
                    chromosome_family=chromosome_family,
                    description=recommendation.rationale,
                    priority=policy.default_new_gene_priority,
                    active=True,
                    tags=["feedback-created"],
                )

                genes_by_id[gene_id] = gene
                new_gene_ids.append(gene_id)

            old_priority = gene.priority
            new_priority = old_priority

            action = str(recommendation.action).upper()

            if action == "STRENGTHEN":
                new_priority = min(
                    policy.max_priority,
                    old_priority + policy.priority_increment,
                )

            elif action == "DEPRIORITIZE":
                new_priority = max(
                    policy.min_priority,
                    old_priority - policy.priority_increment,
                )

            elif action == "DISABLE":
                gene.active = False
                deactivated_gene_ids.append(gene_id)
                new_priority = old_priority

            if new_priority != old_priority:
                gene.priority = new_priority

                updates.append(
                    GenePriorityUpdate(
                        gene_id=gene_id,
                        chromosome_family=chromosome_family,
                        old_priority=old_priority,
                        new_priority=new_priority,
                        delta=new_priority - old_priority,
                        reason=recommendation.rationale,
                    )
                )

        refined_genome = ArchitecturalGenome(
            id=deterministic_id(
                "architectural_genome",
                {
                    "base_genome_id": genome.id,
                    "version": genome.version + 1,
                    "genes": [
                        gene.model_dump(mode="json")
                        for gene in genes_by_id.values()
                    ],
                },
            ),
            version=genome.version + 1,
            base_ref=genome.id,
            genes=list(genes_by_id.values()),
            created_at=utcnow().isoformat(),
        )

        plan = GenomeRefinementPlan(
            id=deterministic_id(
                "genome_refinement_plan",
                {
                    "genome_id": genome.id,
                    "refined_genome_id": refined_genome.id,
                    "recommendation_count": len(recommendations),
                },
            ),
            genome_id=genome.id,
            updates=updates,
            new_genes=new_gene_ids,
            deactivated_genes=deactivated_gene_ids,
            rationale=(
                f"Refined genome using {len(recommendations)} "
                "feedback recommendation(s)."
            ),
            created_at=utcnow().isoformat(),
        )

        return plan, refined_genome

    def _resolve_chromosome_family(
        self,
        recommendation: GenomeRefinementRecommendation,
    ) -> ChromosomeFamily:
        try:
            return ChromosomeFamily(recommendation.chromosome_family)
        except ValueError:
            return OBJECTIVE_TO_CHROMOSOME_FAMILY.get(
                recommendation.objective,
                ChromosomeFamily.GOVERNANCE,
            )


def create_default_genome(target_ref: str) -> ArchitecturalGenome:
    """Create a default genome containing one gene per chromosome family."""

    genes = [
        GenomeGene(
            gene_id=f"{family.value.lower()}_gene",
            chromosome_family=family,
            description=f"Default {family.value} chromosome gene.",
            priority=0.5,
            active=True,
        )
        for family in ChromosomeFamily
    ]

    return ArchitecturalGenome(
        id=deterministic_id(
            "architectural_genome",
            {
                "target_ref": target_ref,
                "version": 1,
                "genes": [gene.model_dump(mode="json") for gene in genes],
            },
        ),
        version=1,
        base_ref=target_ref,
        genes=genes,
        created_at=utcnow().isoformat(),
    )
