"""
ISR Service Model — operational units with operations, dependencies, and events.
Technology-neutral: no framework controllers, no HTTP handlers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Optional

from constitutional_architecture.isr.model.fields import Field


@unique
class OperationType(str, Enum):
    COMMAND = "command"
    QUERY = "query"
    EVENT_HANDLER = "event_handler"
    SCHEDULED = "scheduled"
    INTERNAL = "internal"


@dataclass(frozen=True)
class Operation:
    id: str
    name: str
    operation_type: OperationType = OperationType.COMMAND
    description: str = ""
    input_schema: tuple[Field, ...] = ()
    output_schema: tuple[Field, ...] = ()
    is_idempotent: bool = False
    is_public: bool = True
    required_permissions: tuple[str, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ServiceDependency:
    target_service_id: str
    dependency_type: str = "runtime"
    is_required: bool = True
    description: str = ""


@dataclass(frozen=True)
class Service:
    id: str
    name: str
    description: str = ""
    operations: tuple[Operation, ...] = ()
    dependencies: tuple[ServiceDependency, ...] = ()
    emitted_events: tuple[str, ...] = ()
    consumed_events: tuple[str, ...] = ()
    is_stateless: bool = True
    metadata: dict[str, str] = field(default_factory=dict)

    def get_operation(self, name: str) -> Optional[Operation]:
        for op in self.operations:
            if op.name == name:
                return op
        return None