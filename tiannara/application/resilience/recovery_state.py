"""35.3 Recovery state machine -- explicit, no collapse."""
from __future__ import annotations
from enum import Enum

class RecoveryState(str, Enum):
    NOT_STARTED="NOT_STARTED"; DETECTED="DETECTED"; CONTAINED="CONTAINED"; RECOVERING="RECOVERING"; RECOVERED="RECOVERED"; FAILED="FAILED"; BOUNDED="BOUNDED"
    def can_transition_to(self, nxt: "RecoveryState") -> bool:
        order = [RecoveryState.NOT_STARTED, RecoveryState.DETECTED, RecoveryState.CONTAINED, RecoveryState.RECOVERING, RecoveryState.RECOVERED]
        if self==RecoveryState.BOUNDED or nxt==RecoveryState.BOUNDED:
            return False
        if nxt==RecoveryState.FAILED:
            return True
        if self==RecoveryState.FAILED:
            return False
        try:
            return order.index(nxt) == order.index(self)+1
        except ValueError:
            return False
