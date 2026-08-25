import type { EvidenceRecord } from '@esap/observation-client';
import { useObservationFetch } from './useObservationFetch';

export function useEvidence(
  evidenceId: string | null,
): ReturnType<typeof useObservationFetch<EvidenceRecord>> {
  return useObservationFetch<EvidenceRecord>(
    evidenceId === null ? null : `/evidence/${encodeURIComponent(evidenceId)}`,
  );
}
