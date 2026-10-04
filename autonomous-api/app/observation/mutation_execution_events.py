"""Observable ESAP mutation execution outcomes."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.observation.gateway.dispatcher import EventDispatcher


class MutationExecutionObserved(BaseModel):
    model_config = ConfigDict(frozen=True)
    surface: str = Field(min_length=1)
    operation: str = Field(min_length=1)
    target: str = Field(min_length=1)
    status: str = Field(pattern="^(EXECUTED|FAILED|ABORTED)$")
    reason: str | None = None
    evidenceDigest: str | None = None


async def emit_mutation_execution(
    dispatcher: EventDispatcher,
    *,
    stream_id: str,
    surface: str,
    operation: str,
    target: str,
    status: str,
    correlation_id: str,
    generation: int,
    evidence_digest: str | None = None,
    reason: str | None = None,
    causation_id: str | None = None,
):
    payload = MutationExecutionObserved(
        surface=surface,
        operation=operation,
        target=target,
        status=status,
        reason=reason,
        evidenceDigest=evidence_digest,
    )
    return await dispatcher.emit(
        stream_id=stream_id,
        event_type="mutation.execution",
        payload=payload,
        correlation_id=correlation_id,
        generation=generation,
        causation_id=causation_id,
    )
