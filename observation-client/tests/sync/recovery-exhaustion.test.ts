import { describe, it, expect } from 'vitest';
import { LiveProjection } from '../../src/sync/LiveProjection.js';
import { ObservationApiError } from '../../src/transport/errors.js';
import {
  FakeEventStream,
  FakeReplaySource,
  FakeSnapshotSource,
  counterReducer,
  makeEnvelope,
  flush,
  type CounterPayload,
  type CounterState,
} from '../helpers.js';

describe('LiveProjection — replay exhaustion triggers resync', () => {
  it('falls back to snapshot when replay is exhausted', async () => {
    const stream = new FakeEventStream();
    const snapshot = new FakeSnapshotSource({
      state: { total: 500 },
      streamId: 'stream-test',
      sequence: 9,
    });
    const replay = new FakeReplaySource(async () => {
      throw new ObservationApiError(409, 'SYNC_REPLAY_EXHAUSTED', null, 'exhausted');
    });

    const projection = new LiveProjection<CounterState, CounterPayload>({
      streamId: 'stream-test',
      initialState: { total: 0 },
      reducer: counterReducer,
      snapshotSource: snapshot,
      replaySource: replay,
      eventStream: stream,
      options: { checkpointIntervalMs: 1_000_000, stalenessPollMs: 1_000_000 },
    });
    await projection.start();

    // Hydrated from snapshot seq 9 → expects 10. Now receive 12 → gap.
    expect(projection.getState().total).toBe(500);
    expect(projection.getStatus().appliedSequence).toBe(9);

    stream.push(makeEnvelope<CounterPayload>({ sequence: 12, payload: { delta: 1 } }));
    await flush();

    // Replay exhausted → resync from snapshot (total back to 500), pending dropped.
    expect(projection.getState().total).toBe(500);
    expect(projection.getStatus().state).toBe('healthy');
    expect(projection.metrics().snapshotFetches).toBeGreaterThanOrEqual(2);
  });
});