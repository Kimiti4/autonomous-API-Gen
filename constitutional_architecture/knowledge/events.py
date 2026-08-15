"""
Knowledge Engine Events.

Event bus for knowledge lifecycle events.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, unique
from typing import Any, Callable


@unique
class KnowledgeEventType(str, Enum):
    KNOWLEDGE_ADDED = "knowledge_added"
    PATTERN_DETECTED = "pattern_detected"
    ANTI_PATTERN_DETECTED = "anti_pattern_detected"
    COMPATIBILITY_UPDATED = "compatibility_updated"
    REASONING_COMPLETED = "reasoning_completed"
    RECOMMENDATION_GENERATED = "recommendation_generated"
    KNOWLEDGE_QUERIED = "knowledge_queried"
    KNOWLEDGE_PERSISTED = "knowledge_persisted"
    KNOWLEDGE_LOADED = "knowledge_loaded"


@dataclass(frozen=True)
class KnowledgeEvent:
    event_type: KnowledgeEventType
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    data: dict[str, Any] = field(default_factory=dict)


class KnowledgeEventBus:

    def __init__(self) -> None:
        self._handlers: dict[KnowledgeEventType, list[Callable]] = {}
        self._global_handlers: list[Callable] = []
        self._history: list[KnowledgeEvent] = []

    def subscribe(self, event_type: KnowledgeEventType, handler: Callable) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    def subscribe_all(self, handler: Callable) -> None:
        self._global_handlers.append(handler)

    def publish(self, event: KnowledgeEvent) -> None:
        self._history.append(event)
        for handler in self._handlers.get(event.event_type, []):
            handler(event)
        for handler in self._global_handlers:
            handler(event)

    @property
    def history(self) -> list[KnowledgeEvent]:
        return list(self._history)
