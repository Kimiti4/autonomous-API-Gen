"""V1-07 Postgres concurrency validation -- requires real Postgres."""
import asyncio
import pytest

pytestmark = pytest.mark.integration

@pytest.mark.asyncio
async def test_atomic_counter_no_gaps_under_concurrency(pg_sequence_store):
    n_writers, m_increments = 20, 500
    async def writer():
        return [await pg_sequence_store.next("stress-stream") for _ in range(m_increments)]
    results = await asyncio.gather(*(writer() for _ in range(n_writers)))
    all_seqs = [s for batch in results for s in batch]
    assert len(all_seqs) == n_writers * m_increments
    assert len(set(all_seqs)) == len(all_seqs), "duplicate sequences detected"
    assert sorted(all_seqs) == list(range(n_writers * m_increments)), "gap detected"

@pytest.mark.asyncio
async def test_envelope_persist_unique_constraint(pg_sequence_store):
    from app.core.contracts.events import EventSource, make_envelope
    src = EventSource(subsystem="test", revision="r")
    env = make_envelope(stream_id="s", sequence=0, event_type="isr.updated", payload={}, correlation_id="c", generation=0, source=src)
    await pg_sequence_store.persist(env)
    with pytest.raises(Exception):
        await pg_sequence_store.persist(env)
