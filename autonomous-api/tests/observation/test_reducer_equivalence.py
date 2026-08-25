import json, os
from pathlib import Path
from types import SimpleNamespace
import pytest
from app.observation.readmodel.reducer import CompositeObservationReducer, initial_state

class EventTypes:
    FITNESS_EVALUATED = "fitness.evaluated"
    CANDIDATE_PROMOTED = "candidate.promoted"
    GOVERNANCE_DECISION_MADE = "governance.decision_made"
    HEARTBEAT = "observation.heartbeat"

VECTORS_PATH = Path(os.getenv("REDUCER_VECTORS_PATH", str(Path(__file__).resolve().parents[2] / "observation-client/tests/fixtures/reducer_vectors.json")))

def _evt(seq, event_type, payload, generation=0, occurred="2026-08-23T00:00:00Z"):
    return {"eventId": f"e{seq}", "streamId": "s", "sequence": seq, "eventType": event_type, "occurredAt": occurred, "correlationId": "c", "causationId": None, "generation": generation, "source": {"subsystem": "t", "revision": "r"}, "payload": payload}

_CANONICAL_EVENTS = {
    "fitness_then_candidate_upsert": [
        _evt(0, EventTypes.FITNESS_EVALUATED, {"generation": 1, "score": 0.9}, generation=1),
        _evt(1, EventTypes.CANDIDATE_PROMOTED, {"candidateId": "a", "v": 1}, generation=1, occurred="2026-08-23T00:00:01Z"),
        _evt(2, EventTypes.CANDIDATE_PROMOTED, {"candidateId": "a", "v": 2}, generation=1, occurred="2026-08-23T00:00:02Z"),
    ],
}

def _fold(events):
    reducer = CompositeObservationReducer()
    state = initial_state()
    for e in events:
        env = SimpleNamespace(eventType=e["eventType"], payload=e["payload"], generation=e["generation"], occurredAt=e["occurredAt"])
        state = reducer.fold(state, env)
    return state

def _build_vectors():
    return {name: {"events": events, "expected": _fold(events)} for name, events in _CANONICAL_EVENTS.items()}

def test_heartbeat_does_not_touch_meta():
    reducer = CompositeObservationReducer()
    state = initial_state()
    env = SimpleNamespace(eventType=EventTypes.HEARTBEAT, payload={}, generation=7, occurredAt="2026-08-23T00:00:00Z")
    assert reducer.fold(state, env) == state
