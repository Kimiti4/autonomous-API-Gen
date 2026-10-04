"""Turn ESAP rejection counterfactuals into bounded improvement plans."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .rejection_analysis import CounterfactualRequirement, RejectionRecord


@dataclass(frozen=True)
class CounterfactualImprovement:
    objective: str
    direction: str
    current_value: float
    target_value: float
    delta: float
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class CounterfactualPlan:
    candidate_architecture_id: str
    rejection_reasons: tuple[str, ...]
    improvements: tuple[CounterfactualImprovement, ...]
    bounded: bool


def materialize_counterfactual_plan(
    rejection: RejectionRecord,
    requirements: Sequence[CounterfactualRequirement],
) -> CounterfactualPlan:
    if rejection.status != "rejected":
        raise ValueError("counterfactual-plan-requires-rejection")
    if any(r.candidate_architecture_id != rejection.candidate_architecture_id for r in requirements):
        raise ValueError("counterfactual-requirement-candidate-mismatch")

    improvements = tuple(
        CounterfactualImprovement(
            objective=r.objective,
            direction=r.direction,
            current_value=r.current_value,
            target_value=r.required_value,
            delta=r.delta,
            evidence=r.evidence,
        )
        for r in sorted(
            requirements,
            key=lambda x: (x.objective, x.direction, x.current_value, x.required_value),
        )
    )
    return CounterfactualPlan(
        candidate_architecture_id=rejection.candidate_architecture_id,
        rejection_reasons=rejection.reasons,
        improvements=improvements,
        bounded=True,
    )
