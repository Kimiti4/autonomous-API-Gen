"""GAP-01 acceptance: monotonic sequences, no gaps, safe interleaving."""
from __future__ import annotations

import asyncio

import pytest

from app.core.contracts.events import EventSource, make_envelope
from app.observation.sequences.memory import InMemorySequenceStore


@pytest.mark.asyncio
async def test_monotonic_no_gaps_single_stream():
    store = InMemorySequenceStore()
    seqs = [await store.next("s1") for _ in range(10_000)]
    assert seqs == list(range(10_000))


@pytest.mark.asyncio
async def test_concurrent_streams_are_independent():
    store = InMemorySequenceStore()

    async def burn(stream):
        return [await store.next(stream) for _ in range(100)]

    a, b = await asyncio.gather(burn("s1"), burn("s2"))
    assert a == list(range(100))
    assert b == list(range(100))


@pytest.mark.asyncio
async def test_replay_is_ascending_and_bounded():
    store = InMemorySequenceStore()
    src = EventSource(subsystem="test", revision="abc123")
    for i in range(5):
        env = make_envelope(
            stream_id="s",
            sequence=await store.next("s"),
            event_type="isr.updated",
            payload={"i": i},
            correlation_id="c",
            generation=0,
            source=src,
        )
        await store.persist(env)
    got = await store.replay("s", after=1, limit=2)
    assert [e.sequence for e in got] == [2, 3]


@pytest.mark.asyncio
async def test_envelope_integrity_hash_is_payload_canonical_json():
    from app.core.ids import content_hash

    src = EventSource(subsystem="test", revision="r")
    payload = {"b": 2, "a": 1}
    env = make_envelope(
        stream_id="s", sequence=0, event_type="isr.updated",
        payload=payload, correlation_id="c", generation=0, source=src,
    )
    assert env.integrity is not None
    assert env.integrity.contentHash == content_hash(payload)


@pytest.mark.asyncio
async def test_event_ids_are_uuidv7_time_sortable():
    import uuid

    src = EventSource(subsystem="test", revision="r")
    e1 = make_envelope(
        stream_id="s", sequence=0, event_type="isr.updated",
        payload={}, correlation_id="c", generation=0, source=src,
    )
    assert e1.eventId.version == 7