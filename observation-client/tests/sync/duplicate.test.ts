import { describe, it, expect } from 'vitest';
import { LruSet } from '../../src/sync/LruSet.js';
import { DuplicateGuard } from '../../src/sync/DuplicateGuard.js';

describe('LruSet', () => {
  it('evicts oldest beyond capacity', () => {
    const set = new LruSet(2);
    set.add('a');
    set.add('b');
    set.add('c'); // evicts 'a'
    expect(set.has('a')).toBe(false);
    expect(set.has('b')).toBe(true);
    expect(set.has('c')).toBe(true);
  });

  it('refreshes recency on access', () => {
    const set = new LruSet(2);
    set.add('a');
    set.add('b');
    set.has('a'); // 'a' becomes most recent
    set.add('c'); // evicts 'b'
    expect(set.has('a')).toBe(true);
    expect(set.has('b')).toBe(false);
  });
});

describe('DuplicateGuard', () => {
  it('detects and marks duplicates', () => {
    const guard = new DuplicateGuard(10);
    expect(guard.isDuplicate('e1')).toBe(false);
    guard.markProcessed('e1');
    expect(guard.isDuplicate('e1')).toBe(true);
  });
});