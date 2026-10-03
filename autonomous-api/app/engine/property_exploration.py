"""Property-based workflow exploration primitives.

Generates deterministic scenario families from architecture semantics without
pretending that generated cases are exhaustive proofs.
"""
from __future__ import annotations
from dataclasses import dataclass
from itertools import combinations
from .state_machine_ir import StateMachineIR
from .workflow_analysis import analyze_races


@dataclass(frozen=True)
class PropertyScenario:
    scenario_id: str
    category: str
    actions: tuple[str, ...]
    property: str


def derive_property_scenarios(sm: StateMachineIR) -> tuple[PropertyScenario, ...]:
    out: list[PropertyScenario] = []
    transitions = sm.transitions

    for t in transitions:
        out.append(PropertyScenario(
            f"{sm.machine_id}:prop:repeat:{t.transition_id}",
            "replay",
            (t.trigger, t.trigger),
            "repeating a transition cannot violate declared invariants",
        ))
        if t.effects:
            out.append(PropertyScenario(
                f"{sm.machine_id}:prop:effect:{t.transition_id}",
                "effect-idempotency",
                (t.trigger, "retry", t.trigger),
                "retrying an effect does not create an unauthorized duplicate effect",
            ))

    for a, b in combinations(transitions, 2):
        if a.source == b.source:
            out.append(PropertyScenario(
                f"{sm.machine_id}:prop:order:{a.transition_id}:{b.transition_id}",
                "ordering",
                (a.trigger, b.trigger),
                "valid ordering preserves state-machine invariants or is rejected",
            ))
            out.append(PropertyScenario(
                f"{sm.machine_id}:prop:reverse:{a.transition_id}:{b.transition_id}",
                "ordering",
                (b.trigger, a.trigger),
                "reverse ordering preserves invariants or is rejected",
            ))

    for race in analyze_races(sm):
        out.append(PropertyScenario(
            f"{race.race_id}:concurrent",
            "concurrency",
            (race.trigger_a, race.trigger_b, "concurrent"),
            "concurrent shared effects remain authorized and consistent",
        ))

    return tuple(out)


def mutation_targets(sm: StateMachineIR) -> tuple[str, ...]:
    return tuple(sorted({
        effect
        for transition in sm.transitions
        for effect in transition.effects
    }))
