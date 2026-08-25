import type { ObservationError } from '../contracts/errors.js';

export type ProjectionHealth =
  | 'initializing'
  | 'healthy'
  | 'degraded'
  | 'stale'
  | 'desynchronized'
  | 'unavailable';

export interface ProjectionStatus {
  readonly state: ProjectionHealth;
  readonly streamId: string;
  readonly authoritativeSequence: number;
  readonly appliedSequence: number;
  readonly lastSuccessfulSyncAt: string | null;
  readonly lastEventAt: string | null;
  readonly lastError: ObservationError | null;
}