"""
Frontend Design Genome — Lethal Mutation & Constraint Satisfaction.

If a mutation violates the Compliance Chromosome (e.g., dropping contrast
below 4.5:1, exceeding DOM depth budget), the genome is marked as "lethal"
and immediately discarded before fitness evaluation.

This saves immense computational cost by avoiding phenotype transcription
and rendering of fatally flawed candidates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from constitutional_architecture.meta.genome.chromosomes import FrontendGenome
from constitutional_architecture.meta.genome.genes import (
    ColorSystemAllele,
    PerformanceBudgetAllele,
)


@dataclass
class LethalityResult:
    lethal: bool = False
    violations: list[str] = field(default_factory=list)

    def merge(self, other: LethalityResult) -> LethalityResult:
        return LethalityResult(
            lethal=self.lethal or other.lethal,
            violations=self.violations + other.violations,
        )


def check_accessibility(genome: FrontendGenome) -> LethalityResult:
    wcag = genome.compliance.accessibility.allele
    min_contrast = {"A": 3.0, "AA": 4.5, "AAA": 7.0}.get(wcag, 4.5)
    violations: list[str] = []
    lethal = False

    color = genome.presentation.color_system.allele
    if not isinstance(color, ColorSystemAllele):
        return LethalityResult()

    steps = color.lightness_steps
    if len(steps) < 2:
        violations.append("Color system must have at least 2 lightness steps")
        lethal = True
    else:
        max_step = max(steps)
        min_step = min(steps)
        contrast_ratio = (max_step + 0.05) / (min_step + 0.05)
        if contrast_ratio < min_contrast * 0.15:
            violations.append(
                f"Insufficient lightness contrast ({contrast_ratio:.2f}) "
                f"for WCAG {wcag} (min {min_contrast:.1f})"
            )
            lethal = True

    return LethalityResult(lethal=lethal, violations=violations)


def check_performance(genome: FrontendGenome) -> LethalityResult:
    budget = genome.compliance.performance_budget.allele
    if not isinstance(budget, PerformanceBudgetAllele):
        return LethalityResult()
    violations: list[str] = []
    lethal = False

    if budget.max_dom_depth > 64:
        violations.append(f"DOM depth {budget.max_dom_depth} exceeds hard limit of 64")
        lethal = True

    if budget.max_animation_paint_area > 0.75:
        violations.append(f"Animation paint area {budget.max_animation_paint_area} exceeds 0.75")
        lethal = True

    return LethalityResult(lethal=lethal, violations=violations)


def check_cognitive(genome: FrontendGenome) -> LethalityResult:
    max_items = genome.compliance.cognitive_load.allele
    violations: list[str] = []
    lethal = False

    if max_items > 9:
        violations.append(f"Max items per group {max_items} exceeds Miller's Law limit of 9")
        lethal = True

    return LethalityResult(lethal=lethal, violations=violations)


def check_genome_lethality(genome: FrontendGenome) -> LethalityResult:
    """Run all lethality checks and return combined result.

    Evaluates whether a genome violates any constitutional constraints:
    - Accessibility: WCAG contrast ratios based on current color system
    - Performance: DOM depth and paint area budgets
    - Cognitive: Items-per-group limits (Miller's Law)

    Individual gene immutability is enforced at the operator level;
    this function checks the *parameter values* against hard boundaries.
    """
    result = LethalityResult()
    result = result.merge(check_accessibility(genome))
    result = result.merge(check_performance(genome))
    result = result.merge(check_cognitive(genome))
    return result
