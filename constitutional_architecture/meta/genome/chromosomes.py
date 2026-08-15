"""
Frontend Design Genome — Chromosome families.

Each chromosome is a collection of related genes that evolve together.
Constitutional constraint: Presentation and Structure chromosomes are
GLOBAL — they apply to the entire application. Only Composition and
Behavior chromosomes may vary at the Page/Feature level.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

from constitutional_architecture.meta.genome.genes import (
    ColorSystemGene, TypographyScaleGene, BaseSizeGene,
    ElevationModelGene, MorphologyGene,
    SpacingScaleGene, GridSystemGene, DensityProfileGene, BreakpointStrategyGene,
    MotionPhysicsGene, DurationScaleGene, InteractionFeedbackGene,
    VisualWeightGene, ComponentVariantGene,
    AccessibilityThresholdGene, PerformanceBudgetGene, CognitiveLoadGene,
    Gene, MutationType,
)


@dataclass
class PresentationChromosome:
    """Visual Semantics — governs look and feel."""
    color_system: ColorSystemGene = field(default_factory=ColorSystemGene)
    typography_scale: TypographyScaleGene = field(default_factory=TypographyScaleGene)
    base_size: BaseSizeGene = field(default_factory=BaseSizeGene)
    elevation: ElevationModelGene = field(default_factory=ElevationModelGene)
    morphology: MorphologyGene = field(default_factory=MorphologyGene)

    @property
    def genes(self) -> list[Gene]:
        return [self.color_system, self.typography_scale, self.base_size,
                self.elevation, self.morphology]

    def mutate(self, rate: float, rng: Optional[random.Random] = None) -> None:
        for gene in self.genes:
            if gene.mutation_type != MutationType.LOCKED:
                gene.mutate(rate, rng)

    def clone(self) -> PresentationChromosome:
        return PresentationChromosome(
            color_system=self.color_system.clone(self.color_system.allele),
            typography_scale=self.typography_scale.clone(self.typography_scale.allele),
            base_size=self.base_size.clone(self.base_size.allele),
            elevation=self.elevation.clone(self.elevation.allele),
            morphology=self.morphology.clone(self.morphology.allele),
        )


@dataclass
class StructureChromosome:
    """Spatial Relationships — governs layout, rhythm, density."""
    spacing_scale: SpacingScaleGene = field(default_factory=SpacingScaleGene)
    grid_system: GridSystemGene = field(default_factory=GridSystemGene)
    density_profile: DensityProfileGene = field(default_factory=DensityProfileGene)
    breakpoint_strategy: BreakpointStrategyGene = field(default_factory=BreakpointStrategyGene)

    @property
    def genes(self) -> list[Gene]:
        return [self.spacing_scale, self.grid_system, self.density_profile,
                self.breakpoint_strategy]

    def mutate(self, rate: float, rng: Optional[random.Random] = None) -> None:
        for gene in self.genes:
            if gene.mutation_type != MutationType.LOCKED:
                gene.mutate(rate, rng)

    def clone(self) -> StructureChromosome:
        return StructureChromosome(
            spacing_scale=self.spacing_scale.clone(self.spacing_scale.allele),
            grid_system=self.grid_system.clone(self.grid_system.allele),
            density_profile=self.density_profile.clone(self.density_profile.allele),
            breakpoint_strategy=self.breakpoint_strategy.clone(self.breakpoint_strategy.allele),
        )


@dataclass
class BehaviorChromosome:
    """Time and State — governs motion, transitions, feedback."""
    motion_physics: MotionPhysicsGene = field(default_factory=MotionPhysicsGene)
    duration_scale: DurationScaleGene = field(default_factory=DurationScaleGene)
    interaction_feedback: InteractionFeedbackGene = field(default_factory=InteractionFeedbackGene)

    @property
    def genes(self) -> list[Gene]:
        return [self.motion_physics, self.duration_scale, self.interaction_feedback]

    def mutate(self, rate: float, rng: Optional[random.Random] = None) -> None:
        for gene in self.genes:
            if gene.mutation_type != MutationType.LOCKED:
                gene.mutate(rate, rng)

    def clone(self) -> BehaviorChromosome:
        return BehaviorChromosome(
            motion_physics=self.motion_physics.clone(self.motion_physics.allele),
            duration_scale=self.duration_scale.clone(self.duration_scale.allele),
            interaction_feedback=self.interaction_feedback.clone(self.interaction_feedback.allele),
        )


@dataclass
class CompositionChromosome:
    """Hierarchy & Assembly — governs how components combine and information is weighted."""
    visual_weight: VisualWeightGene = field(default_factory=VisualWeightGene)
    component_variant: ComponentVariantGene = field(default_factory=ComponentVariantGene)

    @property
    def genes(self) -> list[Gene]:
        return [self.visual_weight, self.component_variant]

    def mutate(self, rate: float, rng: Optional[random.Random] = None) -> None:
        for gene in self.genes:
            if gene.mutation_type != MutationType.LOCKED:
                gene.mutate(rate, rng)

    def clone(self) -> CompositionChromosome:
        return CompositionChromosome(
            visual_weight=self.visual_weight.clone(self.visual_weight.allele),
            component_variant=self.component_variant.clone(self.component_variant.allele),
        )


@dataclass
class ComplianceChromosome:
    """Constitutional Guardrails — heavily guarded / immutable genes.
    These act as the fitness function's hard boundaries."""
    accessibility: AccessibilityThresholdGene = field(default_factory=AccessibilityThresholdGene)
    performance_budget: PerformanceBudgetGene = field(default_factory=PerformanceBudgetGene)
    cognitive_load: CognitiveLoadGene = field(default_factory=CognitiveLoadGene)

    @property
    def genes(self) -> list[Gene]:
        return [self.accessibility, self.performance_budget, self.cognitive_load]

    def mutate(self, rate: float, rng: Optional[random.Random] = None) -> None:
        for gene in self.genes:
            if gene.mutation_type != MutationType.LOCKED:
                gene.mutate(rate, rng)

    def clone(self) -> ComplianceChromosome:
        return ComplianceChromosome(
            accessibility=self.accessibility.clone(self.accessibility.allele),
            performance_budget=self.performance_budget.clone(self.performance_budget.allele),
            cognitive_load=self.cognitive_load.clone(self.cognitive_load.allele),
        )


@dataclass
class FrontendGenome:
    """Complete Design Genome — all five chromosome families."""
    presentation: PresentationChromosome = field(default_factory=PresentationChromosome)
    structure: StructureChromosome = field(default_factory=StructureChromosome)
    behavior: BehaviorChromosome = field(default_factory=BehaviorChromosome)
    composition: CompositionChromosome = field(default_factory=CompositionChromosome)
    compliance: ComplianceChromosome = field(default_factory=ComplianceChromosome)

    @property
    def all_genes(self) -> list[Gene]:
        return (self.presentation.genes + self.structure.genes
                + self.behavior.genes + self.composition.genes
                + self.compliance.genes)

    def mutate(self, rate: float = 0.1, rng: Optional[random.Random] = None) -> None:
        self.presentation.mutate(rate, rng)
        self.structure.mutate(rate, rng)
        self.behavior.mutate(rate, rng)
        self.composition.mutate(rate, rng)
        self.compliance.mutate(rate, rng)

    def clone(self) -> FrontendGenome:
        return FrontendGenome(
            presentation=self.presentation.clone(),
            structure=self.structure.clone(),
            behavior=self.behavior.clone(),
            composition=self.composition.clone(),
            compliance=self.compliance.clone(),
        )
