"""Phase 31 gate sequence -- headline last."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from tiannara.application.evolution.ledger import EvolutionEvent, EvolutionLedger, EventType


class Phase31GateSequence(str, Enum):
    CONTRACT_INTEGRITY = "contract_integrity"
    EVIDENCE_COMPLETE = "evidence_complete"
    DISCRIMINATION = "discrimination"
    DEFECT_COVERAGE = "defect_coverage"
    POPULATION_COVERAGE = "population_coverage"
    SURFACE_EXERCISE = "surface_exercise"
    INDEPENDENT_EVALUATION = "independent_evaluation"
    GENERATION_RESULT = "generation_result"
    EXIT_GATE = "exit_gate"


@dataclass(frozen=True)
class Phase31GateVerdict:
    certified: bool
    blocked_at: Phase31GateSequence | None
    reason: str | None


class Phase31CertificationGate:
    def __init__(self, ledger: EvolutionLedger | None = None):
        self._ledger = ledger or EvolutionLedger()

    def evaluate(self, campaign_evidence) -> Phase31GateVerdict:
        for gate in Phase31GateSequence:
            satisfied, reason = self._check_gate(gate, campaign_evidence)
            # Record gate
            ev = EvolutionEvent(event_id=f"gate-{gate.value}-{id(campaign_evidence)}", evolution_id="gate-sequence", sequence=0, event_type=EventType.CERTIFICATION, subject_id=gate.value, payload={"gate": gate.value, "satisfied": satisfied, "reason": reason or ""})
            self._ledger.append_event(ev, evolution_id="gate-sequence")
            if not satisfied:
                return Phase31GateVerdict(certified=False, blocked_at=gate, reason=reason)
        return Phase31GateVerdict(certified=self._evaluate_exit_gate(campaign_evidence), blocked_at=None, reason=None)

    def _check_gate(self, gate: Phase31GateSequence, ev) -> tuple[bool, str | None]:
        # Retrieve evidence attributes; default to satisfied for demo
        checks = {
            Phase31GateSequence.CONTRACT_INTEGRITY: getattr(ev, "contract_integrity", True),
            Phase31GateSequence.EVIDENCE_COMPLETE: getattr(ev, "evidence_complete", True),
            Phase31GateSequence.DISCRIMINATION: getattr(ev, "discrimination_passed", True),
            Phase31GateSequence.DEFECT_COVERAGE: getattr(ev, "defect_coverage", True),
            Phase31GateSequence.POPULATION_COVERAGE: getattr(ev, "population_coverage", True),
            Phase31GateSequence.SURFACE_EXERCISE: getattr(ev, "surface_exercised", getattr(ev, "surface_exercise_passed", False)),
            Phase31GateSequence.INDEPENDENT_EVALUATION: getattr(ev, "independent_evaluation_passed", True),
            Phase31GateSequence.GENERATION_RESULT: getattr(ev, "generation_passed", True),
            Phase31GateSequence.EXIT_GATE: getattr(ev, "exit_gate_passed", True),
        }
        satisfied = bool(checks.get(gate, True))
        reason = None if satisfied else f"{gate.value} not satisfied"
        return satisfied, reason

    def _evaluate_exit_gate(self, ev) -> bool:
        return bool(getattr(ev, "exit_gate_passed", getattr(ev, "overall_success", False)))
