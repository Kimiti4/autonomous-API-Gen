"""33.1 Security Epistemic State Model -- no collapse."""
from __future__ import annotations

from enum import Enum


class SecurityTestState(str, Enum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NOT_TESTED = "NOT_TESTED"
    BOUNDED = "BOUNDED"
    PASSED = "PASSED"
    FAILED = "FAILED"

    def contributes_to_pass(self) -> bool:
        return self is SecurityTestState.PASSED


class AttackOutcome(str, Enum):
    BLOCKED = "BLOCKED"
    DETECTED = "DETECTED"
    CONTAINED = "CONTAINED"
    MISSED = "MISSED"
    BOUNDED = "BOUNDED"

    def is_success(self) -> bool:
        return self in (AttackOutcome.BLOCKED, AttackOutcome.DETECTED, AttackOutcome.CONTAINED)

    def is_failure(self) -> bool:
        return self is AttackOutcome.MISSED


class RecoveryState(str, Enum):
    NOT_REQUIRED = "NOT_REQUIRED"
    NOT_ATTEMPTED = "NOT_ATTEMPTED"
    BOUNDED = "BOUNDED"
    RECOVERED = "RECOVERED"
    FAILED = "FAILED"
