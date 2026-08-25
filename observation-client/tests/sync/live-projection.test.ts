import { describe, it, expect } from 'vitest';
import { LiveProjection } from '../../src/sync/LiveProjection.js';
import { EventTypes } from '../../src/contracts/envelope.js';
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

function build(opts?: {
  snapshotSequence?: number;
  snapshotTotal?: number;
}) {
  const stream = new FakeEventStream();
  const snapshot = new FakeSnapshotSource({
    state: { total: opts?.snapshotTotal ?? 0 },
    streamId: 'stream-test',
    sequence: opts?.snapshotSequence ?? -1,
  });
  const replay = new FakeReplaySource(async (after) => {
    return { state: {}, sequence: after, replayEvents: [] };
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
  return { projection, stream };
}

describe('LiveProjection — happy path', () => {
  it('hydrates from snapshot and applies expected events', async () => {
    const { projection, stream } = build({ snapshotSequence: -1, snapshotTotal: 0 });
    await projection.start();

    stream.push(makeEnvelope<CounterPayload>({ sequence: 0, payload: { delta: 5 } }));
    await flush();
    expect(projection.getState().total).toBe(5);

    stream.push(makeEnvelope<CounterPayload>({ sequence: 1, payload: { delta: 3 } }));
    await flush();
    expect(projection.getState().total).toBe(8);
    expect(projection.getStatus().appliedSequence).toBe(1);
  });

  it('ignores duplicate eventIds idempotently', async () => {
    const { projection, stream } = build();
    await projection.start();

    const envelope = makeEnvelope<CounterPayload>({ sequence: 0, payload: { delta: 7 } });
    stream.push(envelope);
    await flush();
    stream.push(envelope); // resend
    await flush();

    expect(projection.getState().total).toBe(7);
    expect(projection.metrics().duplicatesIgnored).toBe(1);
  });

  it('ignores stale-sequence events', async () => {
    const { projection, stream } = build();
    await projection.start();

    stream.push(makeEnvelope<CounterPayload>({ sequence: 0, payload: { delta: 1 } }));
    stream.push(makeEnvelope<CounterPayload>({ sequence: 1, payload: { delta: 1 } }));
    await flush();
    stream.push(
      makeEnvelope<CounterPayload>({ sequence: 0, eventId: 'late', payload: { delta: 100 } }),
    );
    await flush();

    expect(projection.getState().total).toBe(2);
  });
});

describe('LiveProjection — gap recovery', () => {
  it('recovers a gap via replay, then applies the pending event', async () => {
    const stream = new FakeEventStream();
    const snapshot = new FakeSnapshotSource({
      state: { total: 0 },
      streamId: 'stream-test',
      sequence: -1,
    });
    const replay = new FakeReplaySource(async (after) => {
      // Fill sequences after=0 → return events 1 and 2.
      expect(after).toBe(0);
      return {
        state: {},
        sequence: 0,
        replayEvents: [
          makeEnvelope<CounterPayload>({ sequence: 1, payload: { delta: 10 } }),
          makeEnvelope<CounterPayload>({ sequence: 2, payload: { delta: 20 } }),
        ],
      };
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

    stream.push(makeEnvelope<CounterPayload>({ sequence: 0, payload: { delta: 1 } }));
    await flush();
    // Gap: expect 1, receive 3.
    stream.push(makeEnvelope<CounterPayload>({ sequence: 3, payload: { delta: 100 } }));
    await flush();

    // 1 + 10 + 20 + 100 = 131
    expect(projection.getState().total).toBe(131);
    expect(projection.getStatus().appliedSequence).toBe(3);
    expect(projection.metrics().gapsDetected).toBe(1);
    expect(projection.metrics().recoveriesSucceeded).toBe(1);
    expect(projection.getStatus().state).toBe('healthy');
  });
});

describe('LiveProjection — heartbeats', () => {
  it('consumes sequence and updates liveness without touching reducer', async () => {
    const { projection, stream } = build();
    await projection.start();

    stream.push(
      makeEnvelope<CounterPayload>({
        sequence: 0,
        eventType: EventTypes.Heartbeat,
        payload: { delta: 999 },
      }),
    );
    await flush();

    expect(projection.getState().total).toBe(0); // reducer NOT called
    expect(projection.getStatus().appliedSequence).toBe(0); // sequence advanced
    expect(projection.metrics().heartbeats).toBe(1);
  });
});

describe('LiveProjection — reducer failure', () => {
  it('marks desynchronized and does not advance on reducer error', async () => {
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
      reducer: () => {
        throw new Error('boom');
      },
      snapshotSource: snapshot,
      replaySource: replay,
      eventStream: stream,
      options: { checkpointIntervalMs: 1_000_000, stalenessPollMs: 1_000_000 },
    });
    await projection.start();

    stream.push(makeEnvelope<CounterPayload>({ sequence: 0, payload: { delta: 1 } }));
    await flush();

    expect(projection.getStatus().state).toBe('desynchronized');
    expect(projection.getStatus().appliedSequence).toBe(-1); // did NOT advance
  });
});