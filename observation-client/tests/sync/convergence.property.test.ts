import { describe, it, expect } from 'vitest';
import { LiveProjection } from '../../src/sync/LiveProjection.js';
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

describe('LiveProjection — convergence property', () => {
  it('converges to the authoritative sum for a clean ordered stream', async () => {
    const n = 200;
    const stream = new FakeEventStream();
    const snapshot = new FakeSnapshotSource({
      state: { total: 0 },
      streamId: 'stream-test',
      sequence: -1,
    });
    const replay = new FakeReplaySource(async (after) => ({
      state: {},
      sequence: after,
      replayEvents: [],
    }));

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

    let expected = 0;
    for (let i = 0; i < n; i++) {
      const delta = (i % 7) + 1;
      expected += delta;
      stream.push(makeEnvelope<CounterPayload>({ sequence: i, payload: { delta } }));
    }
    await flush();

    expect(projection.getState().total).toBe(expected);
    expect(projection.getStatus().appliedSequence).toBe(n - 1);
    expect(projection.getStatus().state).toBe('healthy');
  });
});