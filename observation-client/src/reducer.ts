import { EventTypes, type EvolutionEventEnvelope } from './contracts/envelope.js';
export interface ObservationUiState {
  facets: { isr?: unknown; fitness?: unknown; candidates?: unknown[]; governance?: unknown[]; evolution?: unknown; };
  meta: { generation: number; facetUpdatedAt: Record<string, string> };
}
export function initialUiState(): ObservationUiState {
  return { facets: {}, meta: { generation: 0, facetUpdatedAt: {} } };
}
const FACET_FOR_EVENT: Record<string, string> = {
  [EventTypes.IsrUpdated]: 'isr',
  [EventTypes.FitnessEvaluated]: 'fitness',
  [EventTypes.CandidatePromoted]: 'candidates',
  [EventTypes.GovernanceDecisionMade]: 'governance',
  [EventTypes.EvolutionStageChanged]: 'evolution',
};
export function observationReducer(state: ObservationUiState, envelope: EvolutionEventEnvelope): ObservationUiState {
  const facet = FACET_FOR_EVENT[envelope.eventType];
  if (!facet) return state;
  const facets = applyFacet(state.facets, facet, envelope.payload);
  return { facets, meta: { generation: envelope.generation, facetUpdatedAt: { ...state.meta.facetUpdatedAt, [facet]: envelope.occurredAt } } };
}
function applyFacet(facets: ObservationUiState['facets'], facet: string, payload: unknown): ObservationUiState['facets'] {
  if (facet === 'candidates') {
    const list = [...(facets.candidates ?? [])];
    const cid = (payload as { candidateId?: string } | null)?.candidateId;
    const idx = cid != null ? list.findIndex((c) => (c as { candidateId?: string })?.candidateId === cid) : -1;
    if (idx >= 0) list[idx] = payload; else list.push(payload);
    return { ...facets, candidates: list };
  }
  if (facet === 'governance') return { ...facets, governance: [...(facets.governance ?? []), payload] };
  return { ...facets, [facet]: payload };
}
