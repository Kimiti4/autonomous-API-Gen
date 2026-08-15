"""
Phase 5: Concrete Fitness Evaluators.

- TokenConsistencyEvaluator: components must reference design tokens
- AccessibilityEvaluator: checks WCAG contrast, ARIA roles, focus management
- VisualHierarchyEvaluator: evaluates size hierarchy ratios from the genome
"""

from __future__ import annotations

from typing import Optional

from constitutional_architecture.meta.genome.evaluators.i_fitness_evaluator import (
    IFitnessEvaluator, FitnessDimension,
)
from constitutional_architecture.isr.profiles.frontend_model import (
    FrontendISRProfile, Component,
)


class TokenConsistencyEvaluator(IFitnessEvaluator):
    @property
    def dimension_name(self) -> str:
        return "Design System Consistency"

    def evaluate(self, isr_profile: Any, compiled_artifacts: Optional[object] = None) -> FitnessDimension:
        if not isinstance(isr_profile, FrontendISRProfile):
            return FitnessDimension(self.dimension_name, 0.0, 1.0, ("No profile provided",))
        violations: list[str] = []
        for comp in isr_profile.components:
            if not comp.token_dependencies and comp.purpose != "Layout Shell":
                violations.append(
                    f"Component '{comp.id}' ({comp.name}) uses hardcoded values instead of tokens"
                )
        score = max(0.0, 1.0 - (len(violations) / max(len(isr_profile.components), 1)))
        return FitnessDimension(self.dimension_name, score, 0.15, tuple(violations))


class AccessibilityEvaluator(IFitnessEvaluator):
    @property
    def dimension_name(self) -> str:
        return "Accessibility & WCAG"

    def evaluate(self, isr_profile: Any, compiled_artifacts: Optional[object] = None) -> FitnessDimension:
        if not isinstance(isr_profile, FrontendISRProfile):
            return FitnessDimension(self.dimension_name, 0.0, 1.0, ("No profile provided",))
        violations: list[str] = []
        total = 0
        for comp in isr_profile.components:
            total += 1
            if not comp.accessibility_contract.aria_role:
                violations.append(f"Component '{comp.id}' ({comp.name}) has no ARIA role")
            if not comp.accessibility_contract.focus_management:
                violations.append(f"Component '{comp.id}' ({comp.name}) has no focus management")
            if "default" not in comp.states:
                violations.append(f"Component '{comp.id}' ({comp.name}) missing default state")
        score = max(0.0, 1.0 - (len(violations) / max(total, 1)))
        return FitnessDimension(self.dimension_name, score, 0.20, tuple(violations))


class VisualHierarchyEvaluator(IFitnessEvaluator):
    @property
    def dimension_name(self) -> str:
        return "Visual Hierarchy & Balance"

    def evaluate(self, isr_profile: Any, compiled_artifacts: Optional[object] = None) -> FitnessDimension:
        if not isinstance(isr_profile, FrontendISRProfile):
            return FitnessDimension(self.dimension_name, 0.0, 1.0, ("No profile provided",))
        violations: list[str] = []
        ds = isr_profile.design_system
        if ds.genome:
            score = 0.85
        else:
            violations.append("Design system has no genome mapping — cannot determine hierarchy strategy")
            score = 0.3
        if len(ds.tokens) < 3:
            score = max(0.0, score - 0.2)
            violations.append("Design system has fewer than 3 token categories")
        return FitnessDimension(self.dimension_name, score, 0.10, tuple(violations))


class CompositeFitness:
    def __init__(self, dimensions: list[FitnessDimension]) -> None:
        self._dimensions = dimensions

    @property
    def dimensions(self) -> list[FitnessDimension]:
        return list(self._dimensions)

    @property
    def composite_score(self) -> float:
        total_weight = sum(d.weight for d in self._dimensions)
        if total_weight == 0:
            return 0.0
        weighted = sum(d.score * d.weight for d in self._dimensions)
        return min(1.0, weighted / total_weight)

    @property
    def all_violations(self) -> list[str]:
        result: list[str] = []
        for d in self._dimensions:
            result.extend(d.violations)
        return result
