"""GAP-02 acceptance: bounded replay, SYNC_REPLAY_EXHAUSTED, ordered events."""
from __future__ import annotations

import pytest

from app.core.contracts.events import EventSource


@pytest.mark.asyncio
async def test_gap_beyond_window_returns_replay_exhausted(
    client, auth_headers, sequence_store, dispatcher
):
    # Seed a stream with 5 events.
    for i in range(5):
        await dispatcher.emit(
            stream_id="s1",
            event_type="evolution.stage_changed",
            payload={"i": i},
            correlation_id="run-1",
            generation=i,
        )

    # Request a replay larger than the bound (limit=1, gap=6).
    resp = client.get(
        "/observation/state",
        params={"streamId": "s1", "after": -1, "limit": 1},
        headers=auth_headers,
    )
    assert resp.status_code == 409
    body = resp.json()
    assert body["error"]["code"] == "SYNC_REPLAY_EXHAUSTED"
    assert body["recovery"]["action"] == "resync_stream"
    assert body["recovery"]["resyncFromSequence"] == 4


@pytest.mark.asyncio
async def test_reconnect_receives_events_in_order(
    client, auth_headers, dispatcher
):
    for i in range(5):
        await dispatcher.emit(
            stream_id="s2",
            event_type="evolution.stage_changed",
            payload={"i": i},
            correlation_id="run-1",
            generation=i,
        )

    # Simulate disconnect at sequence 2, reconnect, request after=2.
    resp = client.get(
        "/observation/state",
        params={"streamId": "s2", "after": 2, "limit": 1000},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    seqs = [e["sequence"] for e in body["replayEvents"]]
    assert seqs == [3, 4]
    # `sequence` is the point up to which state is consistent.
    assert body["sequence"] == 2
    # AM-3: `state` is materialized AS OF that consistency point.
    assert body["state"]["streamId"] == "s2"
    assert body["state"]["consistentThrough"] == 2
    assert body["state"]["lastEvent"]["sequence"] == 2


@pytest.mark.asyncio
async def test_unknown_stream_returns_envelope(client, auth_headers):
    resp = client.get(
        "/observation/state",
        params={"streamId": "nope", "after": -1},
        headers=auth_headers,
    )
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["code"] == "SYNC_STREAM_NOT_FOUND"
    assert "metadata" in body and "provenance" in body


@pytest.mark.asyncio
async def test_persisted_envelope_round_trip_is_json_identical(
    sequence_store, dispatcher
):
    envelope = await dispatcher.emit(
        stream_id="rt",
        event_type="fitness.evaluated",
        payload={"generation": 1, "best": 0.9},
        correlation_id="run-rt",
        generation=1,
    )
    replayed = await sequence_store.replay("rt", after=-1, limit=10)
    assert len(replayed) == 1
    assert replayed[0].model_dump(mode="json") == envelope.model_dump(mode="json")