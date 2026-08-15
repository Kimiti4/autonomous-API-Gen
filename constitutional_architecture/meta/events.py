"""
Meta-Evolution Lifecycle Events.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, unique
from typing import Any, Callable


@unique
class MetaEventType(str, Enum):
    GENOME_CREATED = "genome_created"
    GENOME_MUTATED = "genome_mutated"
    FITNESS_EVALUATED = "fitness_evaluated"
    SANDBOX_STARTED = "sandbox_started"
    SANDBOX_COMPLETED = "sandbox_completed"
    SANDBOX_FAILED = "sandbox_failed"
    SAFETY_CHECK_PASSED = "safety_check_passed"
    SAFETY_CHECK_FAILED = "safety_check_failed"
    PLATFORM_EVOLVED = "platform_evolved"
    PLATFORM_ROLLBACK = "platform_rollback"
    BENCHMARK_COMPLETED = "benchmark_completed"
    STRATEGY_OPTIMIZED = "strategy_optimized"
    COMPATIBILITY_VERIFIED = "compatibility_verified"
    COMPATIBILITY_FAILED = "compatibility_failed"


@dataclass(frozen=True)
class MetaEvent:
    event_type: MetaEventType
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    data: dict[str, Any] = field(default_factory=dict)


class MetaEventBus:
    """Event bus for meta-evolution lifecycle events."""

    def __init__(self) -> None:
        self._handlers: dict[MetaEventType, list[Callable]] = {}
        self._global_handlers: list[Callable] = []
        self._history: list[MetaEvent] = []

    def subscribe(self, event_type: MetaEventType, handler: Callable) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    def subscribe_all(self, handler: Callable) -> None:
        self._global_handlers.append(handler)

    def publish(self, event: MetaEvent) -> None:
        self._history.append(event)
        for handler in self._handlers.get(event.event_type, []):
            handler(event)
        for handler in self._global_handlers:
            handler(event)

    @property
    def history(self) -> list[MetaEvent]:
        return list(self._history)
