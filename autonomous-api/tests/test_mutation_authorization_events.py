import pytest
from app.core.contracts.events import EventSource
from app.engine.generation_scope import GenerationScope, validate_scope
from app.engine.scope_authorization import MutationIntent
from app.observation.gateway.dispatcher import EventDispatcher
from app.observation.sequences.memory import InMemorySequenceStore
from app.observation.mutation_authorization_events import emit_mutation_authorization


@pytest.mark.asyncio
async def test_authorized_mutation_is_observed():
    store = InMemorySequenceStore()
    d = EventDispatcher(store=store, source=EventSource(subsystem="esap", revision="test"))
    event = await emit_mutation_authorization(
        d, stream_id="p", contract=validate_scope(GenerationScope.FRONTEND_ONLY),
        mutation=MutationIntent("frontend", "edit", "src/App.tsx"),
        correlation_id="c", generation=1,
    )
    assert event.eventType == "mutation.authorization"
    assert event.payload.decision == "AUTHORIZED"


@pytest.mark.asyncio
async def test_blocked_mutation_is_observed_with_reason():
    store = InMemorySequenceStore()
    d = EventDispatcher(store=store, source=EventSource(subsystem="esap", revision="test"))
    event = await emit_mutation_authorization(
        d, stream_id="p", contract=validate_scope(GenerationScope.FRONTEND_ONLY),
        mutation=MutationIntent("backend", "edit", "api/app.py"),
        correlation_id="c", generation=1,
    )
    assert event.payload.decision == "BLOCKED"
    assert "scope-violation" in event.payload.reason


@pytest.mark.asyncio
async def test_authorization_event_is_persisted():
    store = InMemorySequenceStore()
    d = EventDispatcher(store=store, source=EventSource(subsystem="esap", revision="test"))
    await emit_mutation_authorization(
        d, stream_id="p", contract=validate_scope(GenerationScope.API_CONTRACT_ONLY),
        mutation=MutationIntent("frontend", "edit", "src/App.tsx"),
        correlation_id="c", generation=1,
    )
    events = await store.replay("p", -1, 10)
    assert events[0].eventType == "mutation.authorization"
    assert events[0].payload.decision == "BLOCKED"
