"""35.10 Exit gate -- multidimensional, critical dispositive, bounded never certified."""
from __future__ import annotations
from enum import Enum
class Gate(str, Enum):
    CONTRACT_INTEGRITY="CONTRACT_INTEGRITY"; EVIDENCE_COMPLETE="EVIDENCE_COMPLETE"; FAILURE_COVERAGE="FAILURE_COVERAGE"; SURFACE_EXERCISE="SURFACE_EXERCISE"; DETECTION="DETECTION"; CONTAINMENT="CONTAINMENT"; RECOVERY="RECOVERY"; POST_RECOVERY="POST_RECOVERY"; REGRESSION="REGRESSION"; INDEPENDENT="INDEPENDENT"; GENERATION="GENERATION"; EXIT="EXIT"
ORDER=list(Gate)
def evaluate(evidence: dict):
    for g in ORDER:
        if not evidence.get(g.value, True):
            return (False, g)
        if evidence.get("critical_missed"): return (False, Gate.CONTRACT_INTEGRITY)
        if evidence.get("bounded"): return (False, Gate.EVIDENCE_COMPLETE)
    return (evidence.get(Gate.EXIT.value, False), None)
