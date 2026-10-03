"""Technology-neutral state-machine IR for workflow correctness."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class State:
    state_id: str
    terminal: bool = False


@dataclass(frozen=True)
class Transition:
    transition_id: str
    source: str
    target: str
    trigger: str
    guard: str | None = None
    effects: tuple[str, ...] = ()
    compensation: tuple[str, ...] = ()


@dataclass(frozen=True)
class StateMachineIR:
    architecture_id: str
    machine_id: str
    states: tuple[State, ...]
    transitions: tuple[Transition, ...]
    initial_state: str
    invariants: tuple[str, ...] = ()


def validate_state_machine(sm: StateMachineIR) -> tuple[str, ...]:
    errors = []
    states = {s.state_id for s in sm.states}
    if sm.initial_state not in states:
        errors.append("missing-initial-state")
    for t in sm.transitions:
        if t.source not in states:
            errors.append(f"missing-source:{t.source}")
        if t.target not in states:
            errors.append(f"missing-target:{t.target}")
        if t.source == t.target and not t.guard:
            errors.append(f"unguarded-self-transition:{t.transition_id}")
    terminals = {s.state_id for s in sm.states if s.terminal}
    for t in sm.transitions:
        if t.source in terminals:
            errors.append(f"transition-from-terminal:{t.transition_id}")
    return tuple(errors)


def reachable_states(sm: StateMachineIR) -> tuple[str, ...]:
    states = {sm.initial_state}
    changed = True
    while changed:
        changed = False
        for t in sm.transitions:
            if t.source in states and t.target not in states:
                states.add(t.target)
                changed = True
    return tuple(sorted(states))


def find_unreachable_states(sm: StateMachineIR) -> tuple[str, ...]:
    return tuple(sorted({s.state_id for s in sm.states} - set(reachable_states(sm))))


def verify_transition_effects(sm: StateMachineIR) -> tuple[str, ...]:
    errors = []
    for t in sm.transitions:
        if t.effects and not t.trigger:
            errors.append(f"effect-without-trigger:{t.transition_id}")
    return tuple(errors)
