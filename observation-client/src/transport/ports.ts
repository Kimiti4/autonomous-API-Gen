import type { EvolutionEventEnvelope } from '../contracts/envelope.js';

export type Unsubscribe = () => void;

export type StreamLifecycle = 'connecting' | 'open' | 'closed' | 'reconnecting';

/** Authoritative current-state provider (AM-4). */
export interface SnapshotSource<TState> {
  fetch(): Promise<SnapshotResult<TState>>;
}

export interface SnapshotResult<TState> {
  readonly state: TState;
  readonly streamId: string;
  /** Stream sequence the state is consistent with. */
  readonly sequence: number;
}

/** Gap-replay provider backed by GET /observation/state. */
export interface ReplaySource<TPayload> {
  recover(after: number): Promise<ReplayResult<TPayload>>;
}

export interface ReplayResult<TPayload> {
  readonly state: Readonly<Record<string, unknown>>;
  readonly sequence: number;
  readonly replayEvents: readonly EvolutionEventEnvelope<TPayload>[];
}

/** Event transport. Reconnection is transport-level; state recovery is not. */
export interface EventStream<TPayload> {
  connect(): Promise<void>;
  close(): void;
  onEnvelope(handler: (envelope: EvolutionEventEnvelope<TPayload>) => void): Unsubscribe;
  onLifecycle(handler: (state: StreamLifecycle) => void): Unsubscribe;
}