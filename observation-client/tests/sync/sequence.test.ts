import { describe, it, expect } from 'vitest';
import { SequenceTracker } from '../../src/sync/SequenceTracker.js';

describe('SequenceTracker', () => {
  it('classifies expected, stale, and gap', () => {
    const tracker = new SequenceTracker();
    tracker.setFromConsistencyPoint(9); // expects 10
    expect(tracker.classify(10)).toBe('expected');
    expect(tracker.classify(9)).toBe('stale');
    expect(tracker.classify(12)).toBe('gap');
  });

  it('advances expected sequence', () => {
    const tracker = new SequenceTracker();
    tracker.setFromConsistencyPoint(-1); // expects 0
    tracker.advance();
    expect(tracker.expectedSequence).toBe(1);
    expect(tracker.appliedSequence).toBe(0);
  });
});