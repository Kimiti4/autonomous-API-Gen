from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class CompilerEventType(str, Enum):
    COMPILATION_STARTED = "compilation_started"
    COMPILATION_COMPLETED = "compilation_completed"
    PASS_STARTED = "pass_started"
    PASS_COMPLETED = "pass_completed"
    CACHE_HIT = "cache_hit"
    ERROR = "error"


@dataclass(frozen=True)
class CompilerEvent:
    event_type: CompilerEventType
    data: dict[str, Any] = field(default_factory=dict)


class CompilerEventBus:
    def __init__(self) -> None:
        self._handlers: dict[CompilerEventType, list[Callable]] = {}

    def publish(self, event: CompilerEvent) -> None:
        handlers = self._handlers.get(event.event_type, [])
        for handler in handlers:
            handler(event)

    def subscribe(self, event_type: CompilerEventType, handler: Callable) -> None:
        self._handlers.setdefault(event_type, []).append(handler)
