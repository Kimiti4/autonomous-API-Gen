/** Bounded LRU set for duplicate detection (D2: default capacity 10,000). */
export class LruSet {
  private readonly map = new Map<string, true>();

  constructor(private readonly capacity: number) {
    if (capacity <= 0) throw new Error('LruSet capacity must be positive');
  }

  has(value: string): boolean {
    if (!this.map.has(value)) return false;
    // Refresh recency.
    this.map.delete(value);
    this.map.set(value, true);
    return true;
  }

  add(value: string): void {
    if (this.map.has(value)) this.map.delete(value);
    this.map.set(value, true);
    while (this.map.size > this.capacity) {
      const oldest = this.map.keys().next().value;
      if (oldest === undefined) break;
      this.map.delete(oldest);
    }
  }

  get size(): number {
    return this.map.size;
  }

  clear(): void {
    this.map.clear();
  }
}