"""
Frontend Design Genome — Gene definitions.

Each gene encodes a single architectural decision parameter.
Genes are abstract — they store mathematical/structural parameters,
never CSS, Tailwind classes, or framework-specific values.
"""

from __future__ import annotations

import math
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Any, Generic, Optional, TypeVar


T = TypeVar("T")


@unique
class MutationType(str, Enum):
    CONTINUOUS = "continuous"
    DISCRETE = "discrete"
    ENUM = "enum"
    BOOLEAN = "boolean"
    LOCKED = "locked"


@dataclass(frozen=True)
class Bounds(Generic[T]):
    min: T
    max: T
    step: Optional[T] = None


class Gene(ABC, Generic[T]):
    """Abstract base for a single evolvable architectural decision."""

    id: str
    name: str
    chromosome_family: str
    locus: str
    mutation_type: MutationType
    dependencies: tuple[str, ...] = ()
    pleiotropy: tuple[str, ...] = ()

    def __init__(self, allele: T) -> None:
        self._allele = allele

    @property
    def allele(self) -> T:
        return self._allele

    @abstractmethod
    def bounds(self) -> Bounds[T]:
        ...

    @abstractmethod
    def clone(self, allele: T) -> Gene[T]:
        ...

    def mutate(self, rate: float, rng: Optional[random.Random] = None) -> None:
        rng = rng or random.Random()
        b = self.bounds()
        if self.mutation_type == MutationType.LOCKED:
            return
        if self.mutation_type == MutationType.CONTINUOUS:
            delta = (rng.random() * 2 - 1) * rate * (b.max - b.min)
            new_val = self._allele + delta
            if b.step is not None:
                new_val = round(new_val / b.step) * b.step
            self._allele = max(b.min, min(b.max, new_val))
        elif self.mutation_type == MutationType.DISCRETE:
            if isinstance(self._allele, int):
                delta = rng.randint(-max(1, int(rate * (b.max - b.min))),
                                    max(1, int(rate * (b.max - b.min))))
                new_val = self._allele + delta
                new_val = max(int(b.min), min(int(b.max), new_val))
                if b.step is not None:
                    new_val = round(new_val / b.step) * b.step
                self._allele = int(new_val)
        elif self.mutation_type == MutationType.ENUM:
            if isinstance(b.min, list) and len(b.min) > 1:
                current_idx = b.min.index(self._allele) if self._allele in b.min else 0
                options = [i for i in range(len(b.min)) if i != current_idx]
                if options:
                    self._allele = b.min[rng.choice(options)]
        elif self.mutation_type == MutationType.BOOLEAN:
            self._allele = not self._allele


# ==============================================================================
# Presentation Chromosome Genes (Visual Semantics)
# ==============================================================================

@dataclass(frozen=True)
class ColorSystemAllele:
    base_hue: float = 220.0
    saturation: float = 0.70
    lightness_steps: tuple[float, ...] = (0.10, 0.20, 0.35, 0.50, 0.65, 0.80, 0.90)
    semantic_shift: dict[str, float] = field(default_factory=lambda: {
        "success": 120, "warning": 45, "danger": 0, "info": 200,
    })


class ColorSystemGene(Gene[ColorSystemAllele]):
    id = "color-system"
    name = "Color System"
    chromosome_family = "Presentation"
    locus = "DesignSystem.tokens.color"
    mutation_type = MutationType.CONTINUOUS

    def __init__(self, allele: Optional[ColorSystemAllele] = None) -> None:
        super().__init__(allele or ColorSystemAllele())

    def bounds(self) -> Bounds[ColorSystemAllele]:
        return Bounds(ColorSystemAllele(), ColorSystemAllele())

    def clone(self, allele: ColorSystemAllele) -> ColorSystemGene:
        return ColorSystemGene(allele)

    def mutate(self, rate: float, rng: Optional[random.Random] = None) -> None:
        rng = rng or random.Random()
        hue_delta = (rng.random() * 2 - 1) * rate * 30
        sat_delta = (rng.random() * 2 - 1) * rate * 0.2
        new_hue = max(0, min(360, self._allele.base_hue + hue_delta))
        new_sat = max(0.05, min(1.0, self._allele.saturation + sat_delta))
        self._allele = ColorSystemAllele(
            base_hue=round(new_hue, 1),
            saturation=round(new_sat, 2),
            lightness_steps=self._allele.lightness_steps,
            semantic_shift=dict(self._allele.semantic_shift),
        )


class TypographyScaleGene(Gene[float]):
    id = "typography-modular-scale"
    name = "Typography Modular Scale"
    chromosome_family = "Presentation"
    locus = "DesignSystem.tokens.typography.scale"
    mutation_type = MutationType.CONTINUOUS
    pleiotropy = ("line-height-calculation", "vertical-rhythm")

    def __init__(self, allele: float = 1.25) -> None:
        super().__init__(allele)

    def bounds(self) -> Bounds[float]:
        return Bounds(min=1.125, max=1.333, step=0.001)

    def clone(self, allele: float) -> TypographyScaleGene:
        return TypographyScaleGene(allele)


class BaseSizeGene(Gene[int]):
    id = "typography-base-size"
    name = "Typography Base Size"
    chromosome_family = "Presentation"
    locus = "DesignSystem.tokens.typography.baseSize"
    mutation_type = MutationType.DISCRETE
    pleiotropy = ("line-height-calculation",)

    def __init__(self, allele: int = 16) -> None:
        super().__init__(allele)

    def bounds(self) -> Bounds[int]:
        return Bounds(min=14, max=18, step=1)

    def clone(self, allele: int) -> BaseSizeGene:
        return BaseSizeGene(allele)


class ElevationModelGene(Gene[float]):
    id = "elevation-ambient-ratio"
    name = "Elevation Ambient Ratio"
    chromosome_family = "Presentation"
    locus = "DesignSystem.tokens.elevation.ambientRatio"
    mutation_type = MutationType.CONTINUOUS

    def __init__(self, allele: float = 0.3) -> None:
        super().__init__(allele)

    def bounds(self) -> Bounds[float]:
        return Bounds(min=0.1, max=0.6, step=0.01)

    def clone(self, allele: float) -> ElevationModelGene:
        return ElevationModelGene(allele)


@dataclass(frozen=True)
class MorphologyAllele:
    corner_radius_strategy: str = "moderate"
    border_weight_scale: tuple[float, ...] = (0.5, 1.0, 2.0, 4.0)
    glassmorphism_intensity: float = 0.0
    neumorphism_intensity: float = 0.0


class MorphologyGene(Gene[MorphologyAllele]):
    id = "morphology"
    name = "Morphology"
    chromosome_family = "Presentation"
    locus = "DesignSystem.tokens.radius"
    mutation_type = MutationType.ENUM

    def __init__(self, allele: Optional[MorphologyAllele] = None) -> None:
        super().__init__(allele or MorphologyAllele())

    def bounds(self) -> Bounds[MorphologyAllele]:
        return Bounds(
            min=["sharp", "slight", "moderate", "rounded", "pill"],
            max=["sharp", "slight", "moderate", "rounded", "pill"],
        )

    def clone(self, allele: MorphologyAllele) -> MorphologyGene:
        return MorphologyGene(allele)

    def mutate(self, rate: float, rng: Optional[random.Random] = None) -> None:
        rng = rng or random.Random()
        strategies = ["sharp", "slight", "moderate", "rounded", "pill"]
        current = self._allele.corner_radius_strategy
        others = [s for s in strategies if s != current]
        if others:
            new_strategy = rng.choice(others)
            self._allele = MorphologyAllele(
                corner_radius_strategy=new_strategy,
                border_weight_scale=self._allele.border_weight_scale,
                glassmorphism_intensity=self._allele.glassmorphism_intensity,
                neumorphism_intensity=self._allele.neumorphism_intensity,
            )


# ==============================================================================
# Structure Chromosome Genes (Spatial Relationships)
# ==============================================================================

class SpacingScaleGene(Gene[int]):
    id = "spacing-base-unit"
    name = "Spacing Base Unit (px)"
    chromosome_family = "Structure"
    locus = "DesignSystem.tokens.spacing.baseUnit"
    mutation_type = MutationType.DISCRETE
    pleiotropy = ("grid-gutter", "component-padding")

    def __init__(self, allele: int = 4) -> None:
        super().__init__(allele)

    def bounds(self) -> Bounds[int]:
        return Bounds(min=2, max=12, step=1)

    def clone(self, allele: int) -> SpacingScaleGene:
        return SpacingScaleGene(allele)


@dataclass(frozen=True)
class GridSystemAllele:
    column_counts: tuple[int, ...] = (4, 8, 12)
    gutter_to_margin_ratio: float = 0.5
    max_width: int = 1280


class GridSystemGene(Gene[GridSystemAllele]):
    id = "grid-system"
    name = "Grid System"
    chromosome_family = "Structure"
    locus = "DesignSystem.grid"
    mutation_type = MutationType.CONTINUOUS

    def __init__(self, allele: Optional[GridSystemAllele] = None) -> None:
        super().__init__(allele or GridSystemAllele())

    def bounds(self) -> Bounds[GridSystemAllele]:
        return Bounds(GridSystemAllele(), GridSystemAllele())

    def clone(self, allele: GridSystemAllele) -> GridSystemGene:
        return GridSystemGene(allele)

    def mutate(self, rate: float, rng: Optional[random.Random] = None) -> None:
        rng = rng or random.Random()
        ratio = self._allele.gutter_to_margin_ratio + (rng.random() * 2 - 1) * rate * 0.3
        ratio = max(0.2, min(1.0, ratio))
        mw = self._allele.max_width + int((rng.random() * 2 - 1) * rate * 200)
        mw = max(640, min(1920, mw))
        self._allele = GridSystemAllele(
            column_counts=self._allele.column_counts,
            gutter_to_margin_ratio=round(ratio, 2),
            max_width=mw,
        )


class DensityProfileGene(Gene[float]):
    id = "density-profile"
    name = "Density Profile"
    chromosome_family = "Structure"
    locus = "DesignSystem.density"
    mutation_type = MutationType.CONTINUOUS

    def __init__(self, allele: float = 0.5) -> None:
        super().__init__(allele)

    def bounds(self) -> Bounds[float]:
        return Bounds(min=0.0, max=1.0, step=0.05)

    def clone(self, allele: float) -> DensityProfileGene:
        return DensityProfileGene(allele)


@dataclass(frozen=True)
class BreakpointStrategyAllele:
    thresholds: tuple[int, ...] = (640, 768, 1024, 1280, 1536)
    adaptive_density_shift: float = 0.2


class BreakpointStrategyGene(Gene[BreakpointStrategyAllele]):
    id = "breakpoint-strategy"
    name = "Breakpoint Strategy"
    chromosome_family = "Structure"
    locus = "DesignSystem.breakpoints"
    mutation_type = MutationType.CONTINUOUS

    def __init__(self, allele: Optional[BreakpointStrategyAllele] = None) -> None:
        super().__init__(allele or BreakpointStrategyAllele())

    def bounds(self) -> Bounds[BreakpointStrategyAllele]:
        return Bounds(BreakpointStrategyAllele(), BreakpointStrategyAllele())

    def clone(self, allele: BreakpointStrategyAllele) -> BreakpointStrategyGene:
        return BreakpointStrategyGene(allele)

    def mutate(self, rate: float, rng: Optional[random.Random] = None) -> None:
        rng = rng or random.Random()
        shift = self._allele.adaptive_density_shift + (rng.random() * 2 - 1) * rate * 0.2
        shift = max(0.0, min(1.0, shift))
        thresholds = tuple(
            max(320, min(1920, t + int((rng.random() * 2 - 1) * rate * 100)))
            for t in self._allele.thresholds
        )
        self._allele = BreakpointStrategyAllele(
            thresholds=thresholds,
            adaptive_density_shift=round(shift, 2),
        )


# ==============================================================================
# Behavior Chromosome Genes (Time and State)
# ==============================================================================

@dataclass(frozen=True)
class MotionPhysicsAllele:
    spring_tension: float = 180.0
    spring_friction: float = 20.0
    easing_control_points: tuple[float, ...] = (0.4, 0.0, 0.2, 1.0)


class MotionPhysicsGene(Gene[MotionPhysicsAllele]):
    id = "motion-physics"
    name = "Motion Physics"
    chromosome_family = "Behavior"
    locus = "DesignSystem.tokens.motion.physics"
    mutation_type = MutationType.CONTINUOUS

    def __init__(self, allele: Optional[MotionPhysicsAllele] = None) -> None:
        super().__init__(allele or MotionPhysicsAllele())

    def bounds(self) -> Bounds[MotionPhysicsAllele]:
        return Bounds(MotionPhysicsAllele(), MotionPhysicsAllele())

    def clone(self, allele: MotionPhysicsAllele) -> MotionPhysicsGene:
        return MotionPhysicsGene(allele)

    def mutate(self, rate: float, rng: Optional[random.Random] = None) -> None:
        rng = rng or random.Random()
        tension = self._allele.spring_tension + (rng.random() * 2 - 1) * rate * 100
        friction = self._allele.spring_friction + (rng.random() * 2 - 1) * rate * 15
        tension = max(30, min(500, tension))
        friction = max(5, min(50, friction))
        self._allele = MotionPhysicsAllele(
            spring_tension=round(tension, 1),
            spring_friction=round(friction, 1),
            easing_control_points=self._allele.easing_control_points,
        )


class DurationScaleGene(Gene[float]):
    id = "duration-scale"
    name = "Duration Scale"
    chromosome_family = "Behavior"
    locus = "DesignSystem.tokens.motion.duration"
    mutation_type = MutationType.CONTINUOUS

    def __init__(self, allele: float = 200.0) -> None:
        super().__init__(allele)

    def bounds(self) -> Bounds[float]:
        return Bounds(min=100.0, max=500.0, step=10.0)

    def clone(self, allele: float) -> DurationScaleGene:
        return DurationScaleGene(allele)


@dataclass(frozen=True)
class InteractionFeedbackAllele:
    hover_intensity: float = 0.5
    active_compression: float = 0.3
    focus_ring_thickness: float = 2.0
    focus_ring_offset: float = 2.0


class InteractionFeedbackGene(Gene[InteractionFeedbackAllele]):
    id = "interaction-feedback"
    name = "Interaction Feedback"
    chromosome_family = "Behavior"
    locus = "DesignSystem.interaction"
    mutation_type = MutationType.CONTINUOUS

    def __init__(self, allele: Optional[InteractionFeedbackAllele] = None) -> None:
        super().__init__(allele or InteractionFeedbackAllele())

    def bounds(self) -> Bounds[InteractionFeedbackAllele]:
        return Bounds(InteractionFeedbackAllele(), InteractionFeedbackAllele())

    def clone(self, allele: InteractionFeedbackAllele) -> InteractionFeedbackGene:
        return InteractionFeedbackGene(allele)

    def mutate(self, rate: float, rng: Optional[random.Random] = None) -> None:
        rng = rng or random.Random()
        hi = max(0.0, min(1.0, self._allele.hover_intensity + (rng.random() * 2 - 1) * rate * 0.3))
        ac = max(0.0, min(1.0, self._allele.active_compression + (rng.random() * 2 - 1) * rate * 0.3))
        ft = max(1.0, min(6.0, self._allele.focus_ring_thickness + (rng.random() * 2 - 1) * rate * 2))
        fo = max(0.0, min(6.0, self._allele.focus_ring_offset + (rng.random() * 2 - 1) * rate * 2))
        self._allele = InteractionFeedbackAllele(
            hover_intensity=round(hi, 2),
            active_compression=round(ac, 2),
            focus_ring_thickness=round(ft, 1),
            focus_ring_offset=round(fo, 1),
        )


# ==============================================================================
# Composition Chromosome Genes (Hierarchy & Assembly)
# ==============================================================================

@dataclass(frozen=True)
class VisualWeightAllele:
    contrast_distribution: float = 0.5
    size_hierarchy_ratio: float = 1.5
    whitespace_allocation: float = 0.5


class VisualWeightGene(Gene[VisualWeightAllele]):
    id = "visual-weight"
    name = "Visual Weight"
    chromosome_family = "Composition"
    locus = "DesignSystem.composition.visualWeight"
    mutation_type = MutationType.CONTINUOUS

    def __init__(self, allele: Optional[VisualWeightAllele] = None) -> None:
        super().__init__(allele or VisualWeightAllele())

    def bounds(self) -> Bounds[VisualWeightAllele]:
        return Bounds(VisualWeightAllele(), VisualWeightAllele())

    def clone(self, allele: VisualWeightAllele) -> VisualWeightGene:
        return VisualWeightGene(allele)

    def mutate(self, rate: float, rng: Optional[random.Random] = None) -> None:
        rng = rng or random.Random()
        cd = max(0.0, min(1.0, self._allele.contrast_distribution + (rng.random() * 2 - 1) * rate * 0.3))
        sr = max(1.0, min(3.0, self._allele.size_hierarchy_ratio + (rng.random() * 2 - 1) * rate * 0.5))
        wa = max(0.0, min(1.0, self._allele.whitespace_allocation + (rng.random() * 2 - 1) * rate * 0.3))
        self._allele = VisualWeightAllele(
            contrast_distribution=round(cd, 2),
            size_hierarchy_ratio=round(sr, 2),
            whitespace_allocation=round(wa, 2),
        )


@dataclass(frozen=True)
class ComponentVariantAllele:
    allowed_combinations: tuple[tuple[str, str], ...] = ()
    default_selections: dict[str, str] = field(default_factory=dict)


class ComponentVariantGene(Gene[ComponentVariantAllele]):
    id = "component-variant"
    name = "Component Variant Strategy"
    chromosome_family = "Composition"
    locus = "DesignSystem.composition.variants"
    mutation_type = MutationType.LOCKED

    def __init__(self, allele: Optional[ComponentVariantAllele] = None) -> None:
        super().__init__(allele or ComponentVariantAllele())

    def bounds(self) -> Bounds[ComponentVariantAllele]:
        return Bounds(ComponentVariantAllele(), ComponentVariantAllele())

    def clone(self, allele: ComponentVariantAllele) -> ComponentVariantGene:
        return ComponentVariantGene(allele)


# ==============================================================================
# Compliance Chromosome Genes (Constitutional Guardrails)
# ==============================================================================

class AccessibilityThresholdGene(Gene[str]):
    id = "accessibility-threshold"
    name = "Accessibility Threshold (WCAG)"
    chromosome_family = "Compliance"
    locus = "Compliance.accessibility"
    mutation_type = MutationType.ENUM

    def __init__(self, allele: str = "AA") -> None:
        super().__init__(allele)

    def bounds(self) -> Bounds[str]:
        return Bounds(min=["A", "AA", "AAA"], max=["A", "AA", "AAA"])

    def clone(self, allele: str) -> AccessibilityThresholdGene:
        return AccessibilityThresholdGene(allele)

    def mutate(self, rate: float, rng: Optional[random.Random] = None) -> None:
        rng = rng or random.Random()
        levels = ["A", "AA", "AAA"]
        current_idx = levels.index(self._allele)
        if current_idx < len(levels) - 1 and rng.random() < rate:
            self._allele = levels[current_idx + 1]


@dataclass(frozen=True)
class PerformanceBudgetAllele:
    max_dom_depth: int = 32
    max_animation_paint_area: float = 0.5
    max_layout_shift: float = 0.1


class PerformanceBudgetGene(Gene[PerformanceBudgetAllele]):
    id = "performance-budget"
    name = "Performance Budget"
    chromosome_family = "Compliance"
    locus = "Compliance.performance"
    mutation_type = MutationType.LOCKED

    def __init__(self, allele: Optional[PerformanceBudgetAllele] = None) -> None:
        super().__init__(allele or PerformanceBudgetAllele())

    def bounds(self) -> Bounds[PerformanceBudgetAllele]:
        return Bounds(PerformanceBudgetAllele(), PerformanceBudgetAllele())

    def clone(self, allele: PerformanceBudgetAllele) -> PerformanceBudgetGene:
        return PerformanceBudgetGene(allele)


class CognitiveLoadGene(Gene[int]):
    id = "cognitive-load"
    name = "Cognitive Load (Max Items per Group)"
    chromosome_family = "Compliance"
    locus = "Compliance.cognitive"
    mutation_type = MutationType.LOCKED

    def __init__(self, allele: int = 7) -> None:
        super().__init__(allele)

    def bounds(self) -> Bounds[int]:
        return Bounds(min=5, max=9, step=1)

    def clone(self, allele: int) -> CognitiveLoadGene:
        return CognitiveLoadGene(allele)


# ==============================================================================
# Convenience: gene registry
# ==============================================================================

GENE_REGISTRY: dict[str, type[Gene]] = {
    "color-system": ColorSystemGene,
    "typography-modular-scale": TypographyScaleGene,
    "typography-base-size": BaseSizeGene,
    "elevation-ambient-ratio": ElevationModelGene,
    "morphology": MorphologyGene,
    "spacing-base-unit": SpacingScaleGene,
    "grid-system": GridSystemGene,
    "density-profile": DensityProfileGene,
    "breakpoint-strategy": BreakpointStrategyGene,
    "motion-physics": MotionPhysicsGene,
    "duration-scale": DurationScaleGene,
    "interaction-feedback": InteractionFeedbackGene,
    "visual-weight": VisualWeightGene,
    "component-variant": ComponentVariantGene,
    "accessibility-threshold": AccessibilityThresholdGene,
    "performance-budget": PerformanceBudgetGene,
    "cognitive-load": CognitiveLoadGene,
}
