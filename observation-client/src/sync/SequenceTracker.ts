export type SequenceVerdict = 'expected' | 'stale' | 'gap';

export class SequenceTracker {
  private expected = 0;
  private initialized = false;

  /** Set the next expected sequence from an authoritative consistency point. */
  setFromConsistencyPoint(sequence: number): void {
    this.expected = sequence + 1;
    this.initialized = true;
  }

  get expectedSequence(): number {
    return this.expected;
  }

  /** Highest applied sequence (expectedSequence - 1). */
  get appliedSequence(): number {
    return this.expected - 1;
  }

  get isInitialized(): boolean {
    return this.initialized;
  }

  classify(sequence: number): SequenceVerdict {
    if (sequence === this.expected) return 'expected';
    if (sequence < this.expected) return 'stale';
    return 'gap';
  }

  advance(): void {
    this.expected += 1;
  }
}