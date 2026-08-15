"""
Frontend Design Genome — Genome Transcriber.

The critical bridge between abstract Genotype and concrete Frontend ISR Profile.

Transcription (Genome → ISR):
  Takes a FrontendGenome's abstract alleles and resolves them into
  concrete ISR entities (tokens, design system, etc.).

The Transcriber is isolated from the Mutator — the Evolution Engine
cannot accidentally inject CSS strings into the genome; it can only
manipulate abstract mathematical alleles, which the Transcriber safely
resolves into the ISR.
"""

from __future__ import annotations

import math
import uuid
from typing import Any, Optional, cast

from constitutional_architecture.meta.genome.chromosomes import FrontendGenome
from constitutional_architecture.meta.genome.genes import (
    ColorSystemAllele, MorphologyAllele, GridSystemAllele,
    BreakpointStrategyAllele, MotionPhysicsAllele, InteractionFeedbackAllele,
    VisualWeightAllele, PerformanceBudgetAllele,
)
from constitutional_architecture.isr.profiles.frontend_model import (
    FrontendISRProfile, DesignSystem, TokenDefinition,
    GenomeMapping, ChromosomeFamily, Component, ComponentNode,
    Layout, Page, Interaction, GridSystem, AccessibilityContract,
    PropertyDefinition, EventDefinition, FitnessTarget,
)


class FrontendGenomeTranscriber:
    """Transcribes a FrontendGenome into a complete FrontendISRProfile.

    The genotype (abstract parameters) → ISR profile (concrete entities).
    """

    _CORNERS: dict[str, float] = {
        "sharp": 0, "slight": 2, "moderate": 4, "rounded": 8, "pill": 9999,
    }

    def transcribe(self, genome: FrontendGenome,
                   design_system_name: str = "Evolved Design System",
                   ) -> FrontendISRProfile:
        tokens = self._build_tokens(genome)
        ds = DesignSystem(
            id=f"ds-{uuid.uuid4().hex[:8]}",
            name=design_system_name,
            tokens=tokens,
            genome=GenomeMapping(
                chromosome_family=ChromosomeFamily.PRESENTATION,
                gene_id="design-system",
                mutation_rate=0.1,
            ),
        )
        return FrontendISRProfile(design_system=ds)

    def _build_tokens(self, genome: FrontendGenome) -> dict[str, dict[str, TokenDefinition]]:
        tokens: dict[str, dict[str, TokenDefinition]] = {}

        # Typography tokens
        tokens["typography"] = self._build_typography_tokens(genome)
        # Color tokens
        tokens["color"] = self._build_color_tokens(genome)
        # Spacing tokens
        tokens["spacing"] = self._build_spacing_tokens(genome)
        # Elevation tokens
        tokens["elevation"] = self._build_elevation_tokens(genome)
        # Motion tokens
        tokens["motion"] = self._build_motion_tokens(genome)
        # Radius tokens
        tokens["radius"] = self._build_radius_tokens(genome)

        return tokens

    def _build_typography_tokens(self, genome: FrontendGenome) -> dict[str, TokenDefinition]:
        scale = genome.presentation.typography_scale.allele
        base = genome.presentation.base_size.allele
        intervals = [-2, -1, 0, 1, 2, 3, 4, 5]
        names = ["xs", "sm", "base", "lg", "xl", "2xl", "3xl", "4xl"]

        tokens: dict[str, TokenDefinition] = {}
        for i, name in zip(intervals, names):
            size = round(base * math.pow(scale, i), 2)
            tokens[f"text-{name}"] = TokenDefinition(
                id=f"text-{name}",
                semantic_role=f"Text {name.capitalize()}",
                category="typography",
                base_value=size,
                description=f"Modular scale step {i}: {base} × {scale}^{i} = {size}px",
            )
        return tokens

    def _build_color_tokens(self, genome: FrontendGenome) -> dict[str, TokenDefinition]:
        allele = genome.presentation.color_system.allele
        if not isinstance(allele, ColorSystemAllele):
            return {}
        tokens: dict[str, TokenDefinition] = {}
        for name, hue_shift in allele.semantic_shift.items():
            base_hue = (allele.base_hue + hue_shift) % 360
            for i, step in enumerate(allele.lightness_steps, 1):
                token_id = f"{name}-{i * 100}"
                tokens[token_id] = TokenDefinition(
                    id=token_id,
                    semantic_role=f"Color {name.capitalize()} {i * 100}",
                    category="color",
                    base_value=f"hsl({base_hue:.0f}, {allele.saturation * 100:.0f}%, {step * 100:.0f}%)",
                    description=f"Semantic color: {name} (hue {base_hue:.0f})",
                )
        return tokens

    def _build_spacing_tokens(self, genome: FrontendGenome) -> dict[str, TokenDefinition]:
        base = genome.structure.spacing_scale.allele
        multipliers = [0.25, 0.5, 1, 1.5, 2, 3, 4, 6, 8]
        names = ["xs", "sm", "md", "lg", "xl", "2xl", "3xl", "4xl", "5xl"]
        tokens: dict[str, TokenDefinition] = {}
        for mult, name in zip(multipliers, names):
            value = int(base * mult)
            tokens[f"space-{name}"] = TokenDefinition(
                id=f"space-{name}",
                semantic_role=f"Spacing {name.capitalize()}",
                category="spacing",
                base_value=f"{value}px",
                description=f"{base}px × {mult} = {value}px",
            )
        return tokens

    def _build_elevation_tokens(self, genome: FrontendGenome) -> dict[str, TokenDefinition]:
        ambient = genome.presentation.elevation.allele
        tokens: dict[str, TokenDefinition] = {}
        for i, level in enumerate([1, 2, 4, 8, 16, 24]):
            offset_y = level
            blur = level * 2
            ambient_opacity = round(ambient * (1.0 - i * 0.1), 2)
            tokens[f"elevation-{level}"] = TokenDefinition(
                id=f"elevation-{level}",
                semantic_role=f"Elevation Level {level}",
                category="elevation",
                base_value=f"0 {offset_y}px {blur}px rgba(0,0,0,{ambient_opacity})",
                description=f"Shadow with ambient ratio {ambient}",
            )
        return tokens

    def _build_motion_tokens(self, genome: FrontendGenome) -> dict[str, TokenDefinition]:
        duration = genome.behavior.duration_scale.allele
        tokens: dict[str, TokenDefinition] = {}
        for label, mult in [("fast", 0.5), ("normal", 1.0), ("slow", 2.0)]:
            tokens[f"duration-{label}"] = TokenDefinition(
                id=f"duration-{label}",
                semantic_role=f"Duration {label.capitalize()}",
                category="motion",
                base_value=f"{duration * mult:.0f}ms",
            )
        return tokens

    def _build_radius_tokens(self, genome: FrontendGenome) -> dict[str, TokenDefinition]:
        allele = genome.presentation.morphology.allele
        if not isinstance(allele, MorphologyAllele):
            return {}
        corner = self._CORNERS.get(allele.corner_radius_strategy, 4)
        tokens: dict[str, TokenDefinition] = {}
        for size, mult in [("sm", 0.5), ("md", 1.0), ("lg", 2.0), ("full", 9999)]:
            if size == "full":
                value = 9999
            else:
                value = round(corner * mult)
            tokens[f"radius-{size}"] = TokenDefinition(
                id=f"radius-{size}",
                semantic_role=f"Radius {size.capitalize()}",
                category="radius",
                base_value=value if size == "full" else f"{value}px",
            )
        return tokens

    def transcribe_to_profile(self, genome: FrontendGenome,
                              components: tuple[Component, ...] = (),
                              layouts: tuple[Layout, ...] = (),
                              pages: tuple[Page, ...] = (),
                              interactions: tuple[Interaction, ...] = (),
                              ) -> FrontendISRProfile:
        profile = self.transcribe(genome)
        return FrontendISRProfile(
            design_system=profile.design_system,
            components=components,
            layouts=layouts,
            pages=pages,
            interactions=interactions,
        )
