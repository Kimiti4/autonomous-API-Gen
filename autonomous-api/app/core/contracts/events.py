"""EvolutionEventEnvelope (POC v1.1 Event Contract v1.0).

Framework-agnostic. No FastAPI / DB / engine imports.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, Literal, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.contracts.provenance import now_utc
from app.core.ids import content_hash, uuid7

T = TypeVar("T")

EventType = Literal[
    "isr.updated",
    "evolution.stage_changed",
    "fitness.evaluated",
    "candidate.promoted",
    "governance.decision_made",
    "operational.feedback_received",
    "observation.error",
    "event.dropped",
    "observation.heartbeat",
    "scope.declared",
    "mutation.authorization",
    "mutation.execution",
    "mutation.verification",
]


class EventSource(BaseModel):
    model_config = ConfigDict(frozen=True)
    subsystem: str = Field(min_length=1)
    revision: str = Field(min_length=1)


class EventIntegrity(BaseModel):
    model_config = ConfigDict(frozen=True)
    contentHash: str = Field(min_length=64, max_length=64)
    signature: Optional[str] = None


class EvolutionEventEnvelope(BaseModel, Generic[T]):
    model_config = ConfigDict(frozen=True)
    eventId: UUID
    streamId: str = Field(min_length=1)
    sequence: int = Field(ge=0)
    eventType: EventType
    occurredAt: datetime
    correlationId: str = Field(min_length=1)
    causationId: Optional[str] = None
    generation: int = Field(ge=0)
    source: EventSource
    payload: T
    integrity: Optional[EventIntegrity] = None


def make_envelope(
    *,
    stream_id: str,
    sequence: int,
    event_type: EventType,
    payload: Any,
    correlation_id: str,
    generation: int,
    source: EventSource,
    causation_id: Optional[str] = None,
) -> EvolutionEventEnvelope:
    if hasattr(payload, "model_dump"):
        hashable = payload.model_dump(mode="json")
    else:
        hashable = payload
    digest = content_hash(hashable)
    return EvolutionEventEnvelope(
        eventId=uuid7(),
        streamId=stream_id,
        sequence=sequence,
        eventType=event_type,
        occurredAt=now_utc(),
        correlationId=correlation_id,
        causationId=causation_id,
        generation=generation,
        source=source,
        payload=payload,
        integrity=EventIntegrity(contentHash=digest),
    )
