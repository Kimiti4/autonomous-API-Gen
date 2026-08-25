import { describe, it, expect } from 'vitest';
import { MemoryCheckpointStore } from '../../src/transport/checkpoint/MemoryCheckpointStore.js';
import { canonicalJson, sha256Hex } from '../../src/util/hash.js';

describe('MemoryCheckpointStore', () => {
  it('saves, loads, and clears', async () => {
    const store = new MemoryCheckpointStore<{ total: number }>();
    const state = { total: 42 };
    const contentHash = await sha256Hex(canonicalJson(state));
    await store.save({
      streamId: 's',
      sequence: 5,
      savedAt: Date.now(),
      state,
      contentHash,
    });

    const loaded = await store.load('s');
    expect(loaded?.state.total).toBe(42);
    expect(loaded?.contentHash).toBe(contentHash);

    await store.clear('s');
    expect(await store.load('s')).toBeNull();
  });
});

describe('canonicalJson', () => {
  it('is order-independent', () => {
    expect(canonicalJson({ b: 1, a: 2 })).toBe(canonicalJson({ a: 2, b: 1 }));
  });
});