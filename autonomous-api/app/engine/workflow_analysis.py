"""Cross-layer workflow analysis: state machines, flows, races and recovery tests."""
from __future__ import annotations
from dataclasses import dataclass
from .flow_ir import FlowIR
from .state_machine_ir import StateMachineIR


@dataclass(frozen=True)
class RaceCandidate:
    race_id: str
    trigger_a: str
    trigger_b: str
    shared_effects: tuple[str, ...]
    mitigation_required: bool = True


@dataclass(frozen=True)
class DerivedVerification:
    verification_id: str
    category: str
    scenario: str
    expected_property: str


def analyze_races(sm: StateMachineIR) -> tuple[RaceCandidate, ...]:
    out = []
    for i, a in enumerate(sm.transitions):
        for b in sm.transitions[i + 1:]:
            if a.source != b.source:
                continue
            shared = tuple(sorted(set(a.effects) & set(b.effects)))
            if shared:
                out.append(RaceCandidate(
                    f"{sm.machine_id}:race:{a.transition_id}:{b.transition_id}",
                    a.trigger, b.trigger, shared,
                ))
    return tuple(out)


def derive_verifications(sm: StateMachineIR, flow: FlowIR) -> tuple[DerivedVerification, ...]:
    out = []
    for t in sm.transitions:
        if t.effects:
            out.append(DerivedVerification(
                f"{sm.machine_id}:transition:{t.transition_id}",
                "state-transition",
                f"trigger {t.trigger} from {t.source}",
                f"target state becomes {t.target} and effects are applied exactly as authorized",
            ))
        if t.compensation:
            out.append(DerivedVerification(
                f"{sm.machine_id}:compensation:{t.transition_id}",
                "recovery",
                f"failure after {t.transition_id}",
                "compensation restores the declared invariant",
            ))
    for r in flow.recoveries:
        out.append(DerivedVerification(
            f"{flow.architecture_id}:failure:{r.failure_id}",
            "failure-recovery",
            r.trigger,
            f"recovery={r.recovery}; retry_limit={r.retry_limit}; idempotency={r.idempotency_required}",
        ))
    for race in analyze_races(sm):
        out.append(DerivedVerification(
            race.race_id, "concurrency",
            f"concurrent triggers: {race.trigger_a} / {race.trigger_b}",
            "shared effects remain consistent and authorized",
        ))
    return tuple(out)


def verify_workflow_alignment(sm: StateMachineIR, flow: FlowIR) -> tuple[str, ...]:
    if sm.architecture_id != flow.architecture_id:
        return ("architecture-id-mismatch",)
    return ()
