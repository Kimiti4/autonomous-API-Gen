"""Generate deterministic, evidence-backed counterexamples for ESAP reasoning."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Any

from .counterexample_analysis import Counterexample, MinimizedCounterexample, minimize_counterexample


@dataclass(frozen=True)
class CounterexampleCandidate:
    scenario_id: str
    actions: tuple[str, ...]
    violated_invariants: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    observations: Mapping[str, Any]


def generate_counterexample(
    *,
    scenario_id: str,
    actions: tuple[str, ...],
    invariant_results: Mapping[str, bool],
    evidence_ids: tuple[str, ...],
    observations: Mapping[str, Any] | None = None,
    fails: Callable[[tuple[str, ...]], bool] | None = None,
) -> MinimizedCounterexample:
    if not scenario_id:
        raise ValueError("counterexample-requires-scenario-id")
    if not actions:
        raise ValueError("counterexample-requires-actions")
    if not evidence_ids:
        raise ValueError("counterexample-requires-evidence")
    violated = tuple(sorted(k for k, passed in invariant_results.items() if not passed))
    if not violated:
        raise ValueError("counterexample-requires-violation")
    cx = Counterexample(scenario_id, actions, violated, tuple(sorted(set(evidence_ids))))
    if fails is None:
        return MinimizedCounterexample(cx.scenario_id, cx.actions, cx.violated_invariants, ())
    minimized = minimize_counterexample(cx, fails)
    return minimized
