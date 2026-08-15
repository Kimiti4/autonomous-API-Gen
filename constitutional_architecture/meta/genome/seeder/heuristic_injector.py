"""
Phase 4: Heuristic Injector — bridges Knowledge Graph → Genome.

Takes abstract patterns from the Knowledge Graph and applies them as
targeted mutations to the Phase 3 Genome BEFORE random evolution begins.
This ensures Generation 0 starts with "senior-level taste" rather than noise.
"""

from __future__ import annotations

import math
from typing import Any, Optional

from constitutional_architecture.meta.genome.knowledge_graph.iknowledge_graph import (
    DesignPattern, GenomeModifier, ChromosomeTarget, ModifierOperation,
)
from constitutional_architecture.meta.genome.chromosomes import (
    FrontendGenome, PresentationChromosome, StructureChromosome,
    BehaviorChromosome, CompositionChromosome,
)
from constitutional_architecture.meta.genome.genes import (
    ColorSystemAllele, MorphologyAllele, GridSystemAllele,
    BreakpointStrategyAllele, MotionPhysicsAllele, InteractionFeedbackAllele,
    VisualWeightAllele, PerformanceBudgetAllele,
)


class HeuristicInjector:
    def inject(self, patterns: list[DesignPattern], genome: FrontendGenome) -> None:
        modifiers = []
        for p in patterns:
            modifiers.extend(p.genome_modifiers)

        for mod in modifiers:
            target = mod.target_chromosome

            if target == ChromosomeTarget.PRESENTATION:
                self._apply_presentation(mod, genome.presentation)
            elif target == ChromosomeTarget.STRUCTURE:
                self._apply_structure(mod, genome.structure)
            elif target == ChromosomeTarget.BEHAVIOR:
                self._apply_behavior(mod, genome.behavior)
            elif target == ChromosomeTarget.COMPOSITION:
                self._apply_composition(mod, genome.composition)

    def _resolve(self, current: Any, operation: ModifierOperation, value: Any) -> Any:
        if operation == ModifierOperation.SET:
            return value
        elif operation == ModifierOperation.ADD:
            return current + value
        elif operation == ModifierOperation.MULTIPLY:
            return current * value
        elif operation == ModifierOperation.CONSTRAIN:
            if isinstance(value, dict):
                lo = value.get("min", -math.inf)
                hi = value.get("max", math.inf)
                return max(lo, min(hi, current))
            return current
        return current

    def _apply_presentation(self, mod: GenomeModifier, chromo: PresentationChromosome) -> None:
        gene = mod.target_gene
        value = mod.value
        if gene == "typography-modular-scale":
            chromo.typography_scale._allele = self._resolve(chromo.typography_scale.allele, mod.operation, value)
        elif gene == "typography-base-size":
            chromo.base_size._allele = self._resolve(chromo.base_size.allele, mod.operation, value)
        elif gene == "color-system":
            if isinstance(value, dict):
                chromo.color_system._allele = ColorSystemAllele(
                    base_hue=value.get("base_hue", chromo.color_system.allele.base_hue),
                    saturation=value.get("saturation", chromo.color_system.allele.saturation),
                    lightness_steps=tuple(value.get("lightness_steps", chromo.color_system.allele.lightness_steps)),
                    semantic_shift=dict(value.get("semantic_shift", chromo.color_system.allele.semantic_shift)),
                )
        elif gene == "elevation-ambient-ratio":
            chromo.elevation._allele = self._resolve(chromo.elevation.allele, mod.operation, value)
        elif gene == "morphology":
            if isinstance(value, dict):
                chromo.morphology._allele = MorphologyAllele(
                    corner_radius_strategy=value.get("corner_radius_strategy", chromo.morphology.allele.corner_radius_strategy),
                    border_weight_scale=tuple(value.get("border_weight_scale", chromo.morphology.allele.border_weight_scale)),
                    glassmorphism_intensity=value.get("glassmorphism_intensity", chromo.morphology.allele.glassmorphism_intensity),
                    neumorphism_intensity=value.get("neumorphism_intensity", chromo.morphology.allele.neumorphism_intensity),
                )

    def _apply_structure(self, mod: GenomeModifier, chromo: StructureChromosome) -> None:
        gene = mod.target_gene
        value = mod.value
        if gene == "spacing-base-unit":
            chromo.spacing_scale._allele = int(self._resolve(chromo.spacing_scale.allele, mod.operation, value))
        elif gene == "grid-system":
            if isinstance(value, dict):
                chromo.grid_system._allele = GridSystemAllele(
                    column_counts=tuple(value.get("column_counts", chromo.grid_system.allele.column_counts)),
                    gutter_to_margin_ratio=value.get("gutter_to_margin_ratio", chromo.grid_system.allele.gutter_to_margin_ratio),
                    max_width=value.get("max_width", chromo.grid_system.allele.max_width),
                )
        elif gene == "density-profile":
            chromo.density_profile._allele = self._resolve(chromo.density_profile.allele, mod.operation, value)
        elif gene == "breakpoint-strategy":
            if isinstance(value, dict):
                chromo.breakpoint_strategy._allele = BreakpointStrategyAllele(
                    thresholds=tuple(value.get("thresholds", chromo.breakpoint_strategy.allele.thresholds)),
                    adaptive_density_shift=value.get("adaptive_density_shift", chromo.breakpoint_strategy.allele.adaptive_density_shift),
                )

    def _apply_behavior(self, mod: GenomeModifier, chromo: BehaviorChromosome) -> None:
        gene = mod.target_gene
        value = mod.value
        if gene == "motion-physics":
            if isinstance(value, dict):
                chromo.motion_physics._allele = MotionPhysicsAllele(
                    spring_tension=value.get("spring_tension", chromo.motion_physics.allele.spring_tension),
                    spring_friction=value.get("spring_friction", chromo.motion_physics.allele.spring_friction),
                    easing_control_points=tuple(value.get("easing_control_points", chromo.motion_physics.allele.easing_control_points)),
                )
        elif gene == "duration-scale":
            chromo.duration_scale._allele = self._resolve(chromo.duration_scale.allele, mod.operation, value)
        elif gene == "interaction-feedback":
            if isinstance(value, dict):
                chromo.interaction_feedback._allele = InteractionFeedbackAllele(
                    hover_intensity=value.get("hover_intensity", chromo.interaction_feedback.allele.hover_intensity),
                    active_compression=value.get("active_compression", chromo.interaction_feedback.allele.active_compression),
                    focus_ring_thickness=value.get("focus_ring_thickness", chromo.interaction_feedback.allele.focus_ring_thickness),
                    focus_ring_offset=value.get("focus_ring_offset", chromo.interaction_feedback.allele.focus_ring_offset),
                )

    def _apply_composition(self, mod: GenomeModifier, chromo: CompositionChromosome) -> None:
        gene = mod.target_gene
        value = mod.value
        if gene == "visual-weight":
            if isinstance(value, dict):
                chromo.visual_weight._allele = VisualWeightAllele(
                    contrast_distribution=value.get("contrast_distribution", chromo.visual_weight.allele.contrast_distribution),
                    size_hierarchy_ratio=value.get("size_hierarchy_ratio", chromo.visual_weight.allele.size_hierarchy_ratio),
                    whitespace_allocation=value.get("whitespace_allocation", chromo.visual_weight.allele.whitespace_allocation),
                )
