"""36.10 Enterprise Gate -- every mandatory control independently evidenced, no composite."""
from enum import Enum
class ControlState(str, Enum):
    CONTROL_IMPLEMENTED="CONTROL_IMPLEMENTED"; CONTROL_VERIFIED="CONTROL_VERIFIED"; EVIDENCE_COMPLETE="EVIDENCE_COMPLETE"; COMPLIANCE_READY="COMPLIANCE_READY"
def is_compliance_ready(state: ControlState) -> bool:
    return state == ControlState.COMPLIANCE_READY
def evaluate_gate(controls: dict) -> bool:
    return all(is_compliance_ready(s) for s in controls.values())
