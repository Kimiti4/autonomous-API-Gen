import pytest
from app.core.contracts.events import EventSource
from app.observation.gateway.dispatcher import EventDispatcher
from app.observation.sequences.memory import InMemorySequenceStore
from app.observation.mutation_verification_events import emit_mutation_verification


@pytest.mark.asyncio
@pytest.mark.parametrize("status,admission", (("VERIFIED","PENDING"),("VERIFIED","ADMITTED"),("FAILED","REJECTED")))
async def test_verification_outcomes_are_observable(status, admission):
    store = InMemorySequenceStore()
    d = EventDispatcher(store=store, source=EventSource(subsystem="esap", revision="test"))
    event = await emit_mutation_verification(
        d, stream_id="p", surface="frontend", operation="edit",
        target="src/App.tsx", status=status, evidence_digest="a"*64,
        correlation_id="c", generation=1, admission=admission,
        reason=None if status == "VERIFIED" else "verification-failed",
    )
    assert event.eventType == "mutation.verification"
    assert event.payload.status == status
    assert event.payload.admission == admission


@pytest.mark.asyncio
async def test_invalid_status_and_admission_are_rejected():
    store = InMemorySequenceStore()
    d = EventDispatcher(store=store, source=EventSource(subsystem="esap", revision="test"))
    with pytest.raises(ValueError):
        await emit_mutation_verification(
            d, stream_id="p", surface="frontend", operation="edit",
            target="src/App.tsx", status="SKIPPED", evidence_digest="a"*64,
            correlation_id="c", generation=1,
        )
    assert await store.current("p") == -1


@pytest.mark.asyncio
async def test_invalid_evidence_digest_is_rejected():
    store = InMemorySequenceStore()
    d = EventDispatcher(store=store, source=EventSource(subsystem="esap", revision="test"))
    with pytest.raises(ValueError):
        await emit_mutation_verification(
            d, stream_id="p", surface="frontend", operation="edit",
            target="src/App.tsx", status="VERIFIED", evidence_digest="bad",
            correlation_id="c", generation=1,
        )
    assert await store.current("p") == -1
