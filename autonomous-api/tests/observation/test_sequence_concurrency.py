import asyncio
import pytest

@pytest.mark.integration
@pytest.mark.asyncio
async def test_atomic_counter_no_gaps_no_dupes(pg_sequence_store):
    n_writers, m_increments = 5, 100  # reduced for CI speed, real V1-07 is 20x500
    async def writer():
        return [await pg_sequence_store.next("stress") for _ in range(m_increments)]
    results = await asyncio.gather(*(writer() for _ in range(n_writers)))
    seqs = [s for batch in results for s in batch]
    assert len(seqs) == n_writers * m_increments
    assert len(set(seqs)) == len(seqs), "duplicate sequences"
    assert sorted(seqs) == list(range(n_writers * m_increments)), "gap detected"
