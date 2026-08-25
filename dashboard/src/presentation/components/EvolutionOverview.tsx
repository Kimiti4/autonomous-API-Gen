import type { ObservationUiState } from '@esap/observation-client';
import { StatCard } from '@/presentation/components/Layout';

interface EvolutionFacet {
  readonly generation?: number;
  readonly activeCandidateId?: string;
}

function lastUpdatedAt(meta: ObservationUiState['meta']): string {
  const stamps = Object.values(meta.facetUpdatedAt);
  if (stamps.length === 0) return '—';
  return stamps.slice().sort().at(-1) ?? '—';
}

/**
 * Overview of the evolution facet as published by the platform. Only
 * fields actually carried by evolution events are rendered.
 */
export function EvolutionOverview({ state }: { state: ObservationUiState }): JSX.Element {
  const facet = (state.facets.evolution ?? {}) as EvolutionFacet;
  const generation = facet.generation ?? state.meta.generation;
  return (
    <div className="grid gap-4 sm:grid-cols-3" data-testid="evolution-overview">
      <StatCard label="Generation" value={generation >= 0 ? String(generation) : '—'} />
      <StatCard label="Active candidate" value={facet.activeCandidateId ?? '—'} />
      <StatCard label="Last facet update" value={lastUpdatedAt(state.meta)} />
    </div>
  );
}
