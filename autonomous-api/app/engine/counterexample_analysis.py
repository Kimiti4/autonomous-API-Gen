"""Counterexample minimization and invariant violation analysis."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Counterexample:
    scenario_id: str
    actions: tuple[str, ...]
    violated_invariants: tuple[str, ...]
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class MinimizedCounterexample:
    scenario_id: str
    actions: tuple[str, ...]
    violated_invariants: tuple[str, ...]
    removed_actions: tuple[str, ...]


def minimize_counterexample(
    counterexample: Counterexample,
    fails: Callable[[tuple[str, ...]], bool],
) -> MinimizedCounterexample:
    actions = list(counterexample.actions)
    removed: list[str] = []
    changed = True
    while changed and len(actions) > 1:
        changed = False
        for i in range(len(actions)):
            candidate = tuple(actions[:i] + actions[i + 1:])
            if candidate and fails(candidate):
                removed.append(actions[i])
                actions = list(candidate)
                changed = True
                break
    return MinimizedCounterexample(
        counterexample.scenario_id,
        tuple(actions),
        counterexample.violated_invariants,
        tuple(removed),
    )


def identify_violations(
    observed_invariants: dict[str, bool],
) -> tuple[str, ...]:
    return tuple(sorted(k for k, satisfied in observed_invariants.items() if not satisfied))


def deliberation_payload(
    counterexample: MinimizedCounterexample,
) -> dict[str, object]:
    return {
        "scenario_id": counterexample.scenario_id,
        "minimal_actions": counterexample.actions,
        "violated_invariants": counterexample.violated_invariants,
        "removed_actions": counterexample.removed_actions,
    }
