"""
Frontend Design Genome — Genome Factory.

Creates initial populations with sensible defaults.
Seeds the evolution engine with a diverse but established set of
architectural design patterns.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

from constitutional_architecture.meta.genome.chromosomes import (
    FrontendGenome, PresentationChromosome, StructureChromosome,
    BehaviorChromosome, CompositionChromosome, ComplianceChromosome,
)
from constitutional_architecture.meta.genome.genes import (
    TypographyScaleGene, ColorSystemGene, ColorSystemAllele,
    SpacingScaleGene, GridSystemGene, GridSystemAllele,
    DensityProfileGene, ElevationModelGene,
    DurationScaleGene, MotionPhysicsGene, MotionPhysicsAllele,
    VisualWeightGene, VisualWeightAllele,
    MorphologyGene, MorphologyAllele,
    BreakpointStrategyGene, BreakpointStrategyAllele,
    InteractionFeedbackGene, InteractionFeedbackAllele,
    AccessibilityThresholdGene,
    PerformanceBudgetGene, PerformanceBudgetAllele,
    CognitiveLoadGene,
)


def _std_rng(seed: Optional[int] = None) -> random.Random:
    return random.Random(seed)


def create_default_genome() -> FrontendGenome:
    """Create the canonical default genome — Generation 0 founder.

    Uses well-established, proven architectural defaults:
    - Major Third typographic scale (1.25)
    - 4px base grid
    - HSL color system with semantic shifts
    - Standard spring physics
    """
    return FrontendGenome()


def create_enterprise_dashboard_genome() -> FrontendGenome:
    """Genome tuned for dense enterprise dashboard layouts."""
    g = FrontendGenome()
    g.structure.spacing_scale = SpacingScaleGene(4)
    g.structure.density_profile = DensityProfileGene(0.8)
    g.structure.grid_system = GridSystemGene(GridSystemAllele(
        column_counts=(12, 16, 24),
        gutter_to_margin_ratio=0.3,
        max_width=1600,
    ))
    g.presentation.typography_scale = TypographyScaleGene(1.2)
    g.presentation.base_size._allele = 13
    g.presentation.color_system = ColorSystemGene(ColorSystemAllele(
        base_hue=210, saturation=0.6,
        semantic_shift={"success": 120, "warning": 30, "danger": 0, "info": 190},
    ))
    g.composition.visual_weight = VisualWeightGene(VisualWeightAllele(
        contrast_distribution=0.7, size_hierarchy_ratio=1.25,
        whitespace_allocation=0.3,
    ))
    return g


def create_consumer_app_genome() -> FrontendGenome:
    """Genome tuned for consumer-facing applications."""
    g = FrontendGenome()
    g.structure.spacing_scale = SpacingScaleGene(8)
    g.structure.density_profile = DensityProfileGene(0.2)
    g.presentation.typography_scale = TypographyScaleGene(1.333)
    g.presentation.base_size._allele = 18
    g.presentation.color_system = ColorSystemGene(ColorSystemAllele(
        base_hue=280, saturation=0.8,
        semantic_shift={"success": 140, "warning": 50, "danger": 350, "info": 200},
    ))
    g.presentation.elevation = ElevationModelGene(0.4)
    g.presentation.morphology = MorphologyGene(MorphologyAllele(
        corner_radius_strategy="rounded", glassmorphism_intensity=0.1,
    ))
    g.behavior.motion_physics = MotionPhysicsGene(MotionPhysicsAllele(
        spring_tension=300, spring_friction=26,
        easing_control_points=(0.16, 1, 0.3, 1),
    ))
    g.behavior.duration_scale = DurationScaleGene(300)
    return g


def create_minimal_genome() -> FrontendGenome:
    """Ultra-minimal genome — for constrained UIs."""
    g = FrontendGenome()
    g.structure.spacing_scale = SpacingScaleGene(2)
    g.structure.density_profile = DensityProfileGene(0.9)
    g.presentation.typography_scale = TypographyScaleGene(1.125)
    g.presentation.base_size._allele = 14
    g.presentation.color_system = ColorSystemGene(ColorSystemAllele(
        base_hue=0, saturation=0.0,
        semantic_shift={"success": 120, "warning": 45, "danger": 0, "info": 210},
    ))
    g.presentation.morphology = MorphologyGene(MorphologyAllele(
        corner_radius_strategy="sharp",
    ))
    g.composition.visual_weight = VisualWeightGene(VisualWeightAllele(
        contrast_distribution=1.0, size_hierarchy_ratio=2.0,
        whitespace_allocation=0.1,
    ))
    g.compliance.accessibility = AccessibilityThresholdGene("AA")
    return g


def create_population(size: int = 6, seed: Optional[int] = None) -> list[FrontendGenome]:
    """Create a diverse initial population with variance.

    Includes the canonical default plus several specialized genomes,
    then fills remaining slots with mutated variants.
    """
    rng = _std_rng(seed)
    founders: list[FrontendGenome] = [
        create_default_genome(),
        create_enterprise_dashboard_genome(),
        create_consumer_app_genome(),
        create_minimal_genome(),
    ]

    while len(founders) < size:
        base = rng.choice(founders[:3])
        variant = base.clone()
        variant.mutate(rate=rng.uniform(0.05, 0.15), rng=rng)
        founders.append(variant)

    return founders[:size]


GENOME_PRESETS: dict[str, callable] = {
    "default": create_default_genome,
    "enterprise-dashboard": create_enterprise_dashboard_genome,
    "consumer-app": create_consumer_app_genome,
    "minimal": create_minimal_genome,
}
