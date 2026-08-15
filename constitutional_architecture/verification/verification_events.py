from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, unique
from typing import Any, Callable


@unique
class VerificationEventType(str, Enum):
    VERIFICATION_STARTED = "verification_started"
    VERIFICATION_COMPLETED = "verification_completed"
    VERIFIER_STARTED = "verifier_started"
    VERIFIER_COMPLETED = "verifier_completed"
    VERIFIER_FAILED = "verifier_failed"
    CHECK_PASSED = "check_passed"
    CHECK_FAILED = "check_failed"
    BLOCKER_FOUND = "blocker_found"
    REPAIR_RECOMMENDED = "repair_recommended"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_DENIED = "approval_denied"
    FITNESS_FEEDBACK_SENT = "fitness_feedback_sent"


@dataclass(frozen=True)
class VerificationEvent:
    event_type: VerificationEventType
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    data: dict[str, Any] = field(default_factory=dict)


class VerificationEventBus:
    def __init__(self) -> None:
        self._handlers: dict[VerificationEventType, list[Callable]] = {}
        self._global_handlers: list[Callable] = []
        self._history: list[VerificationEvent] = []

    def subscribe(self, event_type: VerificationEventType, handler: Callable) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    def subscribe_all(self, handler: Callable) -> None:
        self._global_handlers.append(handler)

    def publish(self, event: VerificationEvent) -> None:
        self._history.append(event)
        for handler in self._handlers.get(event.event_type, []):
            handler(event)
        for handler in self._global_handlers:
            handler(event)

    @property
    def history(self) -> list[VerificationEvent]:
        return list(self._history)

    def get_events(self, event_type: VerificationEventType) -> list[VerificationEvent]:
        return [e for e in self._history if e.event_type == event_type]
