import { LruSet } from './LruSet.js';

export class DuplicateGuard {
  private readonly seen: LruSet;

  constructor(capacity = 10_000) {
    this.seen = new LruSet(capacity);
  }

  isDuplicate(eventId: string): boolean {
    return this.seen.has(eventId);
  }

  markProcessed(eventId: string): void {
    this.seen.add(eventId);
  }

  reset(): void {
    this.seen.clear();
  }
}