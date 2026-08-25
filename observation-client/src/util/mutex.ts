/** Serializes async critical sections. Preserves event application order. */
export class AsyncMutex {
  private queue: Array<() => void> = [];
  private locked = false;

  runExclusive<T>(fn: () => Promise<T>): Promise<T> {
    return this.acquire().then(async () => {
      try {
        return await fn();
      } finally {
        this.release();
      }
    });
  }

  private acquire(): Promise<void> {
    if (!this.locked) {
      this.locked = true;
      return Promise.resolve();
    }
    return new Promise<void>((resolve) => this.queue.push(resolve));
  }

  private release(): void {
    const next = this.queue.shift();
    if (next) next();
    else this.locked = false;
  }
}