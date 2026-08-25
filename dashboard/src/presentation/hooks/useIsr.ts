import type { ISRObservation } from '@esap/observation-client';
import { useObservationFetch } from './useObservationFetch';

export function useIsr(): ReturnType<typeof useObservationFetch<ISRObservation>> {
  return useObservationFetch<ISRObservation>('/isr');
}
