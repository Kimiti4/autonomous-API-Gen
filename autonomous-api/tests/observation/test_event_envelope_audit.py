import pytest
from app.core.contracts.events import EventSource, make_envelope

EVENT_ISR_UPDATED = "isr.updated"

@pytest.mark.asyncio
async def test_1_1_event_id_globally_unique(dispatcher):
    envs = [await dispatcher.emit(stream_id="s", event_type=EVENT_ISR_UPDATED, payload={}, correlation_id="c", generation=0) for _ in range(100)]
    ids = [str(e.eventId) for e in envs]
    assert len(set(ids)) == len(ids)
    assert all(e.eventId.version == 7 for e in envs)

@pytest.mark.asyncio
async def test_1_2_stream_id_scopes_sequence(dispatcher):
    a = await dispatcher.emit(stream_id="A", event_type=EVENT_ISR_UPDATED, payload={}, correlation_id="c", generation=0)
    b = await dispatcher.emit(stream_id="B", event_type=EVENT_ISR_UPDATED, payload={}, correlation_id="c", generation=0)
    assert a.streamId == "A" and b.streamId == "B"
    assert a.sequence == 0 and b.sequence == 0

@pytest.mark.asyncio
async def test_1_3_sequence_strictly_monotonic(dispatcher):
    seqs = [(await dispatcher.emit(stream_id="S", event_type=EVENT_ISR_UPDATED, payload={}, correlation_id="c", generation=0)).sequence for _ in range(100)]
    assert seqs == list(range(100))
