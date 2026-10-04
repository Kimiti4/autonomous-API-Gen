"""Convert bounded ESAP counterfactual requirements into executable repair work."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .counterfactual_plan import CounterfactualPlan


@dataclass(frozen=True)
class CounterfactualWorkItem:
    work_id: str
    candidate_architecture_id: str
    objective: str
    direction: str
    current_value: float
    target_value: float
    delta: float
    evidence: tuple[str, ...]
    acceptance_properties: tuple[str, ...]


@dataclass(frozen=True)
class CounterfactualWorkPlan:
    candidate_architecture_id: str
    work_items: tuple[CounterfactualWorkItem, ...]
    bounded: bool


def materialize_counterfactual_work(
    plan: CounterfactualPlan,
    *,
    work_id_prefix: str,
    acceptance_properties_by_objective: Mapping[str, Sequence[str]],
) -> CounterfactualWorkPlan:
    if not plan.bounded:
        raise ValueError("counterfactual-work-requires-bounded-plan")
    if not work_id_prefix:
        raise ValueError("counterfactual-work-requires-id-prefix")

    items: list[CounterfactualWorkItem] = []
    for index, improvement in enumerate(plan.improvements, start=1):
        properties = tuple(
            str(p) for p in acceptance_properties_by_objective.get(improvement.objective, ())
        )
        if not properties:
            raise ValueError(
                "counterfactual-work-missing-acceptance-properties:"
                + improvement.objective
            )
        items.append(
            CounterfactualWorkItem(
                work_id=f"{work_id_prefix}:{index}",
                candidate_architecture_id=plan.candidate_architecture_id,
                objective=improvement.objective,
                direction=improvement.direction,
                current_value=improvement.current_value,
                target_value=improvement.target_value,
                delta=improvement.delta,
                evidence=improvement.evidence,
                acceptance_properties=properties,
            )
        )

    return CounterfactualWorkPlan(
        candidate_architecture_id=plan.candidate_architecture_id,
        work_items=tuple(items),
        bounded=True,
    )
