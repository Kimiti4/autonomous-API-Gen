import type { ReplaySource, SnapshotSource } from '../transport/ports.js';
import { ObservationApiError } from '../transport/errors.js';
import type { EvolutionEventEnvelope } from '../contracts/envelope.js';

export type RecoveryPlan<TPayload> =
  | {
      kind: 'replay';
      consistencySequence: number;
      events: readonly EvolutionEventEnvelope<TPayload>[];
    }
  | { kind: 'resync' };

/**
 * Decides HOW to close a gap. Execution lives in LiveProjection so all state
 * mutation stays under one mutex.
 */
export class RecoveryCoordinator<TState, TPayload> {
  constructor(
    private readonly replay: ReplaySource<TPayload>,
    private readonly snapshot: SnapshotSource<TState>,
  ) {}

  async plan(missingFrom: number): Promise<RecoveryPlan<TPayload>> {
    const after = missingFrom - 1;
    try {
      const result = await this.replay.recover(after);
      return {
        kind: 'replay',
        consistencySequence: result.sequence,
        events: result.replayEvents,
      };
    } catch (error) {
      if (error instanceof ObservationApiError) {
        if (error.isReplayExhausted || error.isStreamNotFound) {
          return { kind: 'resync' };
        }
      }
      throw error;
    }
  }

  /** Full snapshot rehydration (used after resync or initial start). */
  async snapshotState() {
    return this.snapshot.fetch();
  }
}