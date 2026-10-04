"""Observable mutation authorization decisions for ESAP."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.engine.scope_authorization import MutationIntent, ScopeViolation, authorize_mutation
from app.engine.generation_scope import ScopeContract
from app.observation.gateway.dispatcher import EventDispatcher


class MutationAuthorizationObserved(BaseModel):
    model_config = ConfigDict(frozen=True)
    surface: str = Field(min_length=1)
    operation: str = Field(min_length=1)
    target: str = Field(min_length=1)
    decision: str = Field(pattern="^(AUTHORIZED|BLOCKED)$")
    reason: str | None = None


async def emit_mutation_authorization(
    dispatcher: EventDispatcher,
    *,
    stream_id: str,
    contract: ScopeContract,
    mutation: MutationIntent,
    correlation_id: str,
    generation: int,
    causation_id: str | None = None,
):
    try:
        authorize_mutation(contract, mutation)
    except ScopeViolation as exc:
        payload = MutationAuthorizationObserved(
            surface=mutation.surface,
            operation=mutation.operation,
            target=mutation.target,
            decision="BLOCKED",
            reason=str(exc),
        )
    else:
        payload = MutationAuthorizationObserved(
            surface=mutation.surface,
            operation=mutation.operation,
            target=mutation.target,
            decision="AUTHORIZED",
        )
    return await dispatcher.emit(
        stream_id=stream_id,
        event_type="mutation.authorization",
        payload=payload,
        correlation_id=correlation_id,
        generation=generation,
        causation_id=causation_id,
    )
