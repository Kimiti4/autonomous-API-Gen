"""
Operational Intelligence Events.

Event bus for operational observations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, unique
from typing import Any, Callable


@unique
class OperationalEventType(str, Enum):
    OBSERVATION_RECEIVED = "observation_received"
    OBSERVATION_CLASSIFIED = "observation_classified"
    ANOMALY_DETECTED = "anomaly_detected"
    DRIFT_DETECTED = "drift_detected"
    INCIDENT_CLASSIFIED = "incident_classified"
    FITNESS_SIGNAL_PRODUCED = "fitness_signal_produced"
    RECOMMENDATION_GENERATED = "recommendation_generated"
    METRIC_COLLECTED = "metric_collected"
    TRACE_ANALYZED = "trace_analyzed"
    LOG_PATTERN_DETECTED = "log_pattern_detected"


@dataclass(frozen=True)
class OperationalEvent:
    event_type: OperationalEventType
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    data: dict[str, Any] = field(default_factory=dict)


class OperationalEventBus:
    """Event bus for operational intelligence events."""

    def __init__(self) -> None:
        self._handlers: dict[OperationalEventType, list[Callable]] = {}
        self._global_handlers: list[Callable] = []
        self._history: list[OperationalEvent] = []

    def subscribe(self, event_type: OperationalEventType, handler: Callable) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    def subscribe_all(self, handler: Callable) -> None:
        self._global_handlers.append(handler)

    def publish(self, event: OperationalEvent) -> None:
        self._history.append(event)
        for handler in self._handlers.get(event.event_type, []):
            handler(event)
        for handler in self._global_handlers:
            handler(event)

    @property
    def history(self) -> list[OperationalEvent]:
        return list(self._history)
