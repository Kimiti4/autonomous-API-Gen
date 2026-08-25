import { describe, expect, it } from 'vitest';
import {
  getProjectionStatus,
  resetProjectionStatus,
  setProjectionStatus,
  subscribeProjectionStatus,
} from '@/application/statusStore';
import type { ProjectionStatus } from '@esap/observation-client';

function status(overrides: Partial<ProjectionStatus> = {}): ProjectionStatus {
  return {
    state: 'healthy',
    streamId: 'evolution-main',
    authoritativeSequence: 7,
    appliedSequence: 7,
    lastSuccessfulSyncAt: null,
    lastEventAt: null,
    lastError: null,
    ...overrides,
  };
}

describe('statusStore', () => {
  it('notifies subscribers on set and supports unsubscribe', () => {
    resetProjectionStatus();
    let calls = 0;
    const unsub = subscribeProjectionStatus(() => {
      calls += 1;
    });
    setProjectionStatus(status());
    expect(getProjectionStatus()?.appliedSequence).toBe(7);
    unsub();
    setProjectionStatus(status({ appliedSequence: 8 }));
    expect(calls).toBe(1);
    expect(getProjectionStatus()?.appliedSequence).toBe(8);
  });
});
