import pytest
from app.core.contracts.events import EventSource
from app.observation.gateway.dispatcher import EventDispatcher
from app.observation.sequences.memory import InMemorySequenceStore
from app.observation.mutation_execution_events import emit_mutation_execution


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ("EXECUTED", "FAILED", "ABORTED"))
async def test_execution_outcomes_are_observable(status):
    store = InMemorySequenceStore()
    d = EventDispatcher(store=store, source=EventSource(subsystem="esap", revision="test"))
    event = await emit_mutation_execution(
        d, stream_id="p", surface="frontend", operation="edit",
        target="src/App.tsx", status=status, correlation_id="c", generation=1,
        evidence_digest="a" * 64, reason=None if status == "EXECUTED" else "test-failure",
    )
    assert event.eventType == "mutation.execution"
    assert event.payload.status == status
    assert event.payload.evidenceDigest == "a" * 64


@pytest.mark.asyncio
async def test_invalid_execution_status_is_rejected():
    store = InMemorySequenceStore()
    d = EventDispatcher(store=store, source=EventSource(subsystem="esap", revision="test"))
    with pytest.raises(ValueError):
        await emit_mutation_execution(
            d, stream_id="p", surface="frontend", operation="edit",
            target="src/App.tsx", status="SKIPPED", correlation_id="c", generation=1,
        )
    assert await store.current("p") == -1


@pytest.mark.asyncio
async def test_failure_and_abort_are_explainable():
    store = InMemorySequenceStore()
    d = EventDispatcher(store=store, source=EventSource(subsystem="esap", revision="test"))
    for status in ("FAILED", "ABORTED"):
        event = await emit_mutation_execution(
            d, stream_id="p", surface="backend", operation="edit",
            target="api/app.py", status=status, correlation_id="c", generation=1,
            reason="bounded-failure",
        )
        assert event.payload.reason == "bounded-failure"
