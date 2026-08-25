import type { EvolutionEventEnvelope } from '../src/contracts/envelope.js';
import type {
  EventStream,
  ReplayResult,
  ReplaySource,
  SnapshotResult,
  SnapshotSource,
  StreamLifecycle,
  Unsubscribe,
} from '../src/transport/ports.js';

export function makeEnvelope<TPayload>(
  partial: Partial<EvolutionEventEnvelope<TPayload>> &
    Pick<EvolutionEventEnvelope<TPayload>, 'sequence'>,
): EvolutionEventEnvelope<TPayload> {
  return {
    eventId: partial.eventId ?? `evt-${partial.sequence}`,
    streamId: partial.streamId ?? 'stream-test',
    eventType: partial.eventType ?? 'test.event',
    occurredAt: partial.occurredAt ?? new Date().toISOString(),
    correlationId: partial.correlationId ?? 'corr-1',
    causationId: partial.causationId ?? null,
    generation: partial.generation ?? 0,
    source: partial.source ?? { subsystem: 'test', revision: 'rev-test' },
    payload: partial.payload as TPayload,
    ...partial,
  };
}

export interface CounterPayload {
  delta: number;
}

export type CounterState = { total: number };

export function counterReducer(
  state: CounterState,
  envelope: EvolutionEventEnvelope<CounterPayload>,
): CounterState {
  return { total: state.total + envelope.payload.delta };
}

export class FakeSnapshotSource implements SnapshotSource<CounterState> {
  constructor(private readonly result: SnapshotResult<CounterState>) {}
  async fetch(): Promise<SnapshotResult<CounterState>> {
    return this.result;
  }
}

export class FakeReplaySource implements ReplaySource<CounterPayload> {
  constructor(
    private readonly handler: (after: number) => Promise<ReplayResult<CounterPayload>>,
  ) {}
  async recover(after: number): Promise<ReplayResult<CounterPayload>> {
    return this.handler(after);
  }
}

export class FakeEventStream implements EventStream<CounterPayload> {
  private envelopeHandlers = new Set<(e: EvolutionEventEnvelope<CounterPayload>) => void>();
  private lifecycleHandlers = new Set<(s: StreamLifecycle) => void>();

  async connect(): Promise<void> {
    this.emitLifecycle('open');
  }

  close(): void {
    this.emitLifecycle('closed');
  }

  onEnvelope(handler: (e: EvolutionEventEnvelope<CounterPayload>) => void): Unsubscribe {
    this.envelopeHandlers.add(handler);
    return () => this.envelopeHandlers.delete(handler);
  }

  onLifecycle(handler: (s: StreamLifecycle) => void): Unsubscribe {
    this.lifecycleHandlers.add(handler);
    return () => this.lifecycleHandlers.delete(handler);
  }

  // Test controls
  push(envelope: EvolutionEventEnvelope<CounterPayload>): void {
    for (const handler of this.envelopeHandlers) handler(envelope);
  }

  emitLifecycle(state: StreamLifecycle): void {
    for (const handler of this.lifecycleHandlers) handler(state);
  }
}

/** Wait for queued microtasks/timers to flush. */
export async function flush(): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, 0));
}