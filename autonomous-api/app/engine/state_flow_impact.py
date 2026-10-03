"""State-flow impact propagation across backend and frontend."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class StateTransition:
    flow_id: str
    from_state: str
    event: str
    to_state: str
    authority: str


@dataclass(frozen=True)
class UIStateDependency:
    flow_id: str
    ui_state: str
    backend_state: str
    behavior: str


@dataclass(frozen=True)
class StateImpact:
    flow_id: str
    backend_state: str
    affected_ui_states: tuple[str, ...]
    affected_behaviors: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class StateImpactReport:
    impacts: tuple[StateImpact, ...]


def analyze_state_transition(
    transition: StateTransition,
    dependencies: tuple[UIStateDependency, ...],
) -> StateImpact:
    related = [
        d for d in dependencies
        if d.flow_id == transition.flow_id
        and d.backend_state in {transition.from_state, transition.to_state}
    ]
    ui_states = tuple(sorted({d.ui_state for d in related}))
    behaviors = tuple(sorted({d.behavior for d in related}))
    return StateImpact(
        transition.flow_id,
        transition.to_state,
        ui_states,
        behaviors,
        f"backend transition {transition.from_state}->{transition.to_state} "
        f"via {transition.event} changes frontend-observable state",
    )


def analyze_transitions(
    transitions: tuple[StateTransition, ...],
    dependencies: tuple[UIStateDependency, ...],
) -> StateImpactReport:
    return StateImpactReport(tuple(
        analyze_state_transition(t, dependencies) for t in transitions
    ))


def required_ui_review_behaviors(
    impact: StateImpact,
) -> tuple[str, ...]:
    standard = {"loading", "error", "retry", "cache", "navigation"}
    return tuple(sorted(standard | set(impact.affected_behaviors)))
