"""
Phase 9: Visual Intelligence Engine.

Evaluates the rendered phenotype using analysis of spatial relationships
that cannot be inferred from the ISR alone (layout shift, visual balance).

In a production system, this would use headless browser telemetry.
Here we provide the architectural interface and a heuristic-based implementation.
"""

from __future__ import annotations

from typing import Any, Optional

from constitutional_architecture.meta.genome.evaluators.i_fitness_evaluator import (
    IFitnessEvaluator, FitnessDimension,
)
from constitutional_architecture.isr.profiles.frontend_model import FrontendISRProfile


class VisualIntelligenceEvaluator(IFitnessEvaluator):
    @property
    def dimension_name(self) -> str:
        return "Visual Hierarchy & Phenotype Quality"

    def evaluate(self, isr_profile: Any, compiled_artifacts: Optional[object] = None) -> FitnessDimension:
        if not isinstance(isr_profile, FrontendISRProfile):
            return FitnessDimension(self.dimension_name, 0.0, 0.10, ("No profile provided",))
        violations: list[str] = []
        profile = isr_profile
        score = 0.88

        page_count = len(profile.pages)
        comp_count = len(profile.components)
        layout_count = len(profile.layouts)

        if page_count == 0:
            violations.append("No pages defined — cannot evaluate layout hierarchy")
            score -= 0.3
        if comp_count == 0:
            violations.append("No components defined — cannot evaluate component hierarchy")
            score -= 0.2
        if layout_count == 0:
            violations.append("No layouts defined — cannot evaluate spatial structure")
            score -= 0.2

        ds = profile.design_system
        token_count = sum(len(cat) for cat in ds.tokens.values())
        if token_count < 15:
            violations.append(f"Only {token_count} tokens — sparse design system may lack visual coherence")
            score -= 0.1

        for comp in profile.components:
            if len(comp.states) < 2:
                violations.append(f"Component '{comp.id}' has only {len(comp.states)} state(s) — may lack interactivity feedback")
                score -= 0.05

        score = max(0.0, min(1.0, score))
        return FitnessDimension(self.dimension_name, score, 0.10, tuple(violations))
