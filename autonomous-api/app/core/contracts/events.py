"""EvolutionEventEnvelope (POC v1.1 Event Contract v1.0).

Framework-agnostic. No FastAPI / DB / engine imports.

Invariants enforced here:
1. (streamId, sequence) is the ordering key. No global sequence.
2. eventId is UUIDv7 (time-sortable, globally unique).
3. correlationId is mandatory — missing correlation is a bug, not a default.
4. contentHash is SHA-256 of the canonical JSON payload, computed BEFORE
   envelope wrapping.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, Literal, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.contracts.provenance import now_utc
from app.core.ids import content_hash, uuid7

T = TypeVar("T")

# AM-1: "observation.heartbeat" is an additive liveness signal.
# AM-2 note: the Literal is the known-constants registry; the platform may
# add types in minor versions and clients must tolerate unknown strings.
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
    """POC v1.1 event envelope. (streamId, sequence) is the ordering key."""
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
    """Build an envelope with a computed integrity hash over the payload.

    The hash is over the canonical JSON of the payload alone (before
    envelope wrapping), so integrity survives re-wrapping/replay.
    """
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