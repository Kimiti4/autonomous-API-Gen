import type { DuplicateGuard } from './DuplicateGuard.js';
import type { SequenceTracker } from './SequenceTracker.js';

export type EnvelopeVerdict =
  | { kind: 'duplicate'; reason: 'eventId' | 'stale-sequence' }
  | { kind: 'apply' }
  | { kind: 'gap'; missingFrom: number; received: number };

/** Combines identity-based and position-based classification. */
export class GapDetector {
  constructor(
    private readonly duplicates: DuplicateGuard,
    private readonly tracker: SequenceTracker,
  ) {}

  evaluate(eventId: string, sequence: number): EnvelopeVerdict {
    if (this.duplicates.isDuplicate(eventId)) {
      return { kind: 'duplicate', reason: 'eventId' };
    }
    const verdict = this.tracker.classify(sequence);
    if (verdict === 'expected') return { kind: 'apply' };
    if (verdict === 'stale') return { kind: 'duplicate', reason: 'stale-sequence' };
    return { kind: 'gap', missingFrom: this.tracker.expectedSequence, received: sequence };
  }
}