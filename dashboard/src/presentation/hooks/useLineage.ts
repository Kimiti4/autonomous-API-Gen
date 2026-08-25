import type { CandidateLineage } from '@esap/observation-client';
import { useObservationFetch } from './useObservationFetch';

export function useLineage(
  candidateId: string | null,
): ReturnType<typeof useObservationFetch<CandidateLineage>> {
  return useObservationFetch<CandidateLineage>(
    candidateId === null ? null : `/lineage/candidate/${encodeURIComponent(candidateId)}`,
  );
}
