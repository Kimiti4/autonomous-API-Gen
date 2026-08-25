from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping

from tiannara.application.evolution.ledger import EvolutionEvent, EvolutionLedger, EventType

@dataclass(frozen=True)
class SurfaceClassEvidence:
    class_id: str
    observed_outcomes: Mapping[str, int]
    satisfied: bool
    violations: tuple[str, ...]

@dataclass(frozen=True)
class SurfaceExerciseEvidence:
    per_class: Mapping[str, SurfaceClassEvidence]
    surface_exercised: bool
    violations: tuple[str, ...]

def tally_by_class_and_outcome(campaign_results):
    # campaign_results: iterable of (class_id, outcome)
    from collections import defaultdict
    tally = defaultdict(lambda: defaultdict(int))
    for class_id, outcome in campaign_results:
        tally[class_id][outcome] += 1
    return {k: dict(v) for k, v in tally.items()}

class SurfaceExerciseGate:
    def __init__(self, ledger: EvolutionLedger | None = None):
        self._ledger = ledger or EvolutionLedger()

    def evaluate(self, contract, campaign_results) -> SurfaceExerciseEvidence:
        observed = tally_by_class_and_outcome(campaign_results)
        per_class = {}
        all_violations = []
        for class_id in contract.required_classes:
            req = contract.class_requirements[class_id]
            class_obs = observed.get(class_id, {})
            violations = []
            if sum(class_obs.values()) == 0:
                violations.append(f"{class_id}: challenge class absent from campaign")
            for required in req.required_outcomes:
                if class_obs.get(required, 0) == 0:
                    violations.append(f"{class_id}: required outcome {required} not observed")
            if req.allowed_outcomes:
                for outcome, count in class_obs.items():
                    if count > 0 and outcome not in req.allowed_outcomes:
                        violations.append(f"{class_id}: disallowed outcome {outcome} observed {count}x")
            per_class[class_id] = SurfaceClassEvidence(class_id, class_obs, not violations, tuple(violations))
            all_violations.extend(violations)
        evidence = SurfaceExerciseEvidence(per_class, not all_violations, tuple(all_violations))
        try:
            ev = EvolutionEvent(event_id=f"surface-{id(evidence)}", evolution_id="surface", sequence=0, event_type=EventType.CERTIFICATION, subject_id="surface", payload={"surface_exercised": evidence.surface_exercised, "violations": list(evidence.violations)})
            self._ledger.append_event(ev, evolution_id="surface")
        except Exception:
            pass
        return evidence
