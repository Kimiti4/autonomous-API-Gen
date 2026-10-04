"""Observable ESAP mutation verification outcomes."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.observation.gateway.dispatcher import EventDispatcher


class MutationVerificationObserved(BaseModel):
    model_config = ConfigDict(frozen=True)
    surface: str = Field(min_length=1)
    operation: str = Field(min_length=1)
    target: str = Field(min_length=1)
    status: str = Field(pattern="^(VERIFIED|FAILED)$")
    evidenceDigest: str = Field(min_length=64, max_length=64)
    reason: str | None = None
    admission: str = Field(pattern="^(PENDING|ADMITTED|REJECTED)$")


async def emit_mutation_verification(
    dispatcher: EventDispatcher,
    *,
    stream_id: str,
    surface: str,
    operation: str,
    target: str,
    status: str,
    evidence_digest: str,
    correlation_id: str,
    generation: int,
    admission: str = "PENDING",
    reason: str | None = None,
    causation_id: str | None = None,
):
    payload = MutationVerificationObserved(
        surface=surface,
        operation=operation,
        target=target,
        status=status,
        evidenceDigest=evidence_digest,
        reason=reason,
        admission=admission,
    )
    return await dispatcher.emit(
        stream_id=stream_id,
        event_type="mutation.verification",
        payload=payload,
        correlation_id=correlation_id,
        generation=generation,
        causation_id=causation_id,
    )
