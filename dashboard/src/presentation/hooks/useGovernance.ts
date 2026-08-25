import type { CandidateGovernanceProjection } from '@esap/observation-client';
import { useObservationFetch } from './useObservationFetch';

/**
 * Platform governance projection endpoint. When the route is not yet
 * published by the platform, this surfaces as an error ("unavailable") —
 * the dashboard never fabricates governance data.
 */
export function useGovernance(
  candidateId: string | null,
): ReturnType<typeof useObservationFetch<CandidateGovernanceProjection>> {
  return useObservationFetch<CandidateGovernanceProjection>(
    candidateId === null ? null : `/governance/candidate/${encodeURIComponent(candidateId)}`,
  );
}
