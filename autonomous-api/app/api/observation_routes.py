"""Observation API routes (GAP-03/04/07/02 + AM-3/AM-4 amendments).

All routes are auth-gated (fail-closed) and return enveloped errors.
Dependencies are injected by the composition root via configure_observation().
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.contracts.observations import (
    CapabilityContract,
    FitnessReport,
    ISRObservation,
    ObservationSnapshotWrapper,
    RecoveryResult,
)
from app.core.exceptions import (
    ObservationDomainError,
    ReplayExhaustedError,
    StreamNotFoundError,
)
from app.middleware.security import require_auth
from app.observation.capabilities import build_capabilities
from app.observation.gateway.dispatcher import EventDispatcher
from app.observation.projectors.fitness import FitnessProjector
from app.observation.projectors.isr import IsrProjector
from app.observation.sequences.store import SequenceStore

router = APIRouter(prefix="/observation", tags=["observation"])

# Wired by the composition root (main.py). Fail-closed if unset.
_store: SequenceStore | None = None
_dispatcher: EventDispatcher | None = None
_fitness_projector: FitnessProjector | None = None
_isr_projector: IsrProjector | None = None


def configure_observation(
    *,
    store: SequenceStore,
    dispatcher: EventDispatcher,
    fitness_projector: FitnessProjector | None = None,
    isr_projector: IsrProjector | None = None,
) -> None:
    global _store, _dispatcher, _fitness_projector, _isr_projector
    _store = store
    _dispatcher = dispatcher
    _fitness_projector = fitness_projector
    _isr_projector = isr_projector


def get_store() -> SequenceStore:
    if _store is None:
        raise ObservationDomainError(
            "Observation subsystem not configured",
            context={"operation": "observation_dependency"},
        )
    return _store


def get_fitness_projector() -> FitnessProjector:
    if _fitness_projector is None:
        raise ObservationDomainError(
            "Fitness projector not configured",
            code="PLATFORM_UNAVAILABLE",
            http_status=503,
            context={"operation": "observation_dependency"},
        )
    return _fitness_projector


def get_isr_projector() -> IsrProjector:
    if _isr_projector is None:
        # 503-over-fake policy: unbound binding is reported, never faked.
        raise ObservationDomainError(
            "ISR projection binding is not yet implemented "
            "(declared Phase B audit gap; see CanonicalIsrAccessor contract)",
            code="PLATFORM_UNAVAILABLE",
            http_status=503,
            context={"operation": "observation.isr"},
        )
    return _isr_projector


async def _materialize_state(store: SequenceStore, stream_id: str,
                             sequence: int) -> dict:
    """AM-3: materialized stream state AS OF `sequence`.

    The honest materialization for an event-sourced stream without a
    server-side reducer is a deterministic summary of the log up to the
    consistency point — never a fabricated aggregate.
    """
    last_event = None
    if sequence >= 0:
        tail = await store.replay(stream_id, sequence - 1, 1)
        if tail and tail[0].sequence == sequence:
            last_event = {
                "eventId": str(tail[0].eventId),
                "sequence": tail[0].sequence,
                "eventType": tail[0].eventType,
                "occurredAt": tail[0].occurredAt.isoformat(),
            }
    return {
        "streamId": stream_id,
        "consistentThrough": sequence,
        "lastEvent": last_event,
    }


@router.get("/capabilities", response_model=CapabilityContract)
async def capabilities(
    store: SequenceStore = Depends(get_store),
    _auth=Depends(require_auth),
):
    from app.core.config import get_settings

    settings = get_settings()
    return await build_capabilities(store, settings.APP_VERSION)


@router.get("/fitness", response_model=FitnessReport)
async def fitness(
    generation: int = Query(ge=0),
    projector: FitnessProjector = Depends(get_fitness_projector),
    _auth=Depends(require_auth),
):
    """Authoritative Pareto report — computed by the platform."""
    return await projector.project(generation)


@router.get("/isr", response_model=ISRObservation)
async def isr(_auth=Depends(require_auth)):
    """Flattened ISR observation. 503 until CanonicalIsrAccessor is bound."""
    projector = get_isr_projector()
    return await projector.project()


@router.get("/snapshot", response_model=ObservationSnapshotWrapper)
async def snapshot(
    streamId: str,
    store: SequenceStore = Depends(get_store),
    _auth=Depends(require_auth),
):
    """AM-4 hydration wrapper: current materialized state + its sequence."""
    current = await store.current(streamId)
    if current < 0:
        raise StreamNotFoundError(
            f"Unknown stream: {streamId}",
            context={"streamId": streamId},
        )
    state = await _materialize_state(store, streamId, current)
    return ObservationSnapshotWrapper(
        data=state, streamId=streamId, sequence=current
    )


@router.get("/state", response_model=RecoveryResult)
async def recover_state(
    streamId: str,
    after: int = Query(ge=-1),
    limit: int = Query(default=1000, ge=1, le=1000),
    store: SequenceStore = Depends(get_store),
    _auth=Depends(require_auth),
):
    """Gap recovery: bounded replay after a client disconnect.

    Invariants:
    - Replay is bounded; beyond the bound → SYNC_REPLAY_EXHAUSTED with
      action=resync_stream.
    - AM-3: `state` is the materialized state as of `sequence`; applying
      replayEvents (ascending) yields the current state.
    - replayEvents are returned in strict sequence order.
    """
    current = await store.current(streamId)
    if current < 0:
        raise StreamNotFoundError(
            f"Unknown stream: {streamId}",
            context={"streamId": streamId},
        )

    gap = current - after
    if gap > limit:
        raise ReplayExhaustedError(
            f"Requested replay of {gap} events exceeds window {limit}",
            resync_from=current,
            context={"streamSequence": current},
        )

    events = await store.replay(streamId, after, limit)
    consistent_to = current if not events else events[0].sequence - 1
    state = await _materialize_state(store, streamId, consistent_to)
    return RecoveryResult(
        state=state,
        sequence=consistent_to,
        replayEvents=[e.model_dump(mode="json") for e in events],
    )