"""Engineering solution-space exploration without framework-template bias."""
from __future__ import annotations
from dataclasses import dataclass


STRATEGY_FAMILIES = (
    "modular_monolith", "service_oriented", "event_driven",
    "workflow_oriented", "data_oriented", "edge_first",
)


@dataclass(frozen=True)
class SolutionStrategy:
    strategy_id: str
    family: str
    principles: tuple[str, ...]
    components: tuple[str, ...]
    assumptions: tuple[str, ...]
    intended_strengths: tuple[str, ...]
    known_risks: tuple[str, ...]


@dataclass(frozen=True)
class ExplorationRequest:
    request_id: str
    required_properties: tuple[str, ...]
    forbidden_assumptions: tuple[str, ...] = ()
    minimum_strategies: int = 3


def generate_strategy_space(
    request: ExplorationRequest,
    available_families: tuple[str, ...] = STRATEGY_FAMILIES,
) -> tuple[SolutionStrategy, ...]:
    strategies = []
    for family in available_families:
        if family not in STRATEGY_FAMILIES:
            continue
        assumptions = (f"family:{family}",)
        if any(a in request.forbidden_assumptions for a in assumptions):
            continue
        strategies.append(SolutionStrategy(
            strategy_id=f"{request.request_id}:{family}",
            family=family,
            principles=(family, "requirements-first", "evidence-driven"),
            components=(),
            assumptions=assumptions,
            intended_strengths=request.required_properties,
            known_risks=(),
        ))
    return tuple(strategies)


def require_diversity(
    strategies: tuple[SolutionStrategy, ...],
    minimum: int,
) -> bool:
    return len({s.family for s in strategies}) >= minimum
