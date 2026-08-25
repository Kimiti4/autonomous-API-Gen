from __future__ import annotations
from typing import Any
from observation.readmodel.reducer import ObservationReducer, initial_state
from observation.sequences.store import SequenceStore

class TruthfulnessOracle:
    def __init__(self, reducer: ObservationReducer, store: SequenceStore) -> None:
        self._reducer = reducer
        self._store = store
    async def expected_state(self, stream_id: str) -> dict[str, Any]:
        state = initial_state()
        after = -1
        while True:
            events = await self._store.replay(stream_id, after, limit=1000)
            if not events:
                break
            for envelope in events:
                state = self._reducer.fold(state, envelope)
            after = events[-1].sequence
            if len(events) < 1000:
                break
        return state
    async def assert_truthful(self, stream_id: str, actual: dict[str, Any], label: str) -> None:
        expected = await self.expected_state(stream_id)
        assert actual == expected, f"TRUTHFULNESS VIOLATION [{label}] stream={stream_id}\n  expected={expected}\n  actual={actual}"
