import type { FitnessReport } from '@esap/observation-client';
import { useObservationFetch } from './useObservationFetch';

export function useFitness(
  generation: number | null,
): ReturnType<typeof useObservationFetch<FitnessReport>> {
  return useObservationFetch<FitnessReport>(
    generation === null ? null : `/fitness?generation=${generation}`,
  );
}
