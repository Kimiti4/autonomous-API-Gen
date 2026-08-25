"""33.14 15-gate sequence -- exit last, BOUNDED never CERTIFIED."""
from __future__ import annotations
from enum import Enum
from dataclasses import dataclass
class Gate(str, Enum):
    CONTRACT_INTEGRITY="CONTRACT_INTEGRITY"; SECURITY_ENVIRONMENT_COMPLETE="SECURITY_ENVIRONMENT_COMPLETE"; ATTACK_SURFACE_COVERAGE="ATTACK_SURFACE_COVERAGE"; ATTACK_TAXONOMY_COVERAGE="ATTACK_TAXONOMY_COVERAGE"; EVIDENCE_COMPLETENESS="EVIDENCE_COMPLETENESS"; DISCRIMINATION="DISCRIMINATION"; CRITICAL_VULNERABILITY_GATE="CRITICAL_VULNERABILITY_GATE"; SECURITY_SURFACE_EXERCISE="SECURITY_SURFACE_EXERCISE"; DETECTION_EFFECTIVENESS="DETECTION_EFFECTIVENESS"; CONTAINMENT="CONTAINMENT"; RECOVERY="RECOVERY"; INDEPENDENT_EVALUATION="INDEPENDENT_EVALUATION"; REGRESSION_COVERAGE="REGRESSION_COVERAGE"; GENERATION_RESULT="GENERATION_RESULT"; EXIT_GATE="EXIT_GATE"
ORDER = list(Gate)
@dataclass(frozen=True)
class GateVerdict: certified: bool; blocked_at: Gate|None; reason: str|None
def evaluate_gates(evidence: dict) -> GateVerdict:
    for g in ORDER:
        ok = evidence.get(g.value, True)
        if g==Gate.EXIT_GATE and not all(evidence.get(x.value, True) for x in ORDER[:-1]): return GateVerdict(False, g, "epistemic prerequisite failed")
        if not ok: return GateVerdict(False, g, f"{g.value} failed")
        if g==Gate.CRITICAL_VULNERABILITY_GATE and evidence.get("critical_missed"): return GateVerdict(False, g, "critical missed")
        if g==Gate.EXIT_GATE and evidence.get("bounded"): return GateVerdict(False, g, "bounded")
    return GateVerdict(True, None, None)
