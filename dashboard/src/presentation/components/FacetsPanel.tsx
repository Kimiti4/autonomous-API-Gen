import type { ObservationUiState } from '@esap/observation-client';

/**
 * Renders which facets the projection currently holds. Facet presence is
 * driven purely by applied platform events — absence means "not yet
 * observed", never an error.
 */
export function FacetsPanel({ state }: { state: ObservationUiState }): JSX.Element {
  const facets: Array<[string, boolean]> = [
    ['ISR', state.facets.isr !== undefined],
    ['Fitness', state.facets.fitness !== undefined],
    ['Candidates', state.facets.candidates !== undefined],
    ['Governance', state.facets.governance !== undefined],
    ['Evolution', state.facets.evolution !== undefined],
  ];
  return (
    <div className="flex flex-wrap gap-2" data-testid="facets-panel">
      {facets.map(([name, present]) => (
        <span
          key={name}
          className={`rounded px-2 py-1 text-xs ${
            present ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-200 text-slate-500'
          }`}
        >
          {name} {present ? '· live' : '· not observed'}
        </span>
      ))}
      <span className="rounded bg-slate-100 px-2 py-1 text-xs text-slate-600">
        generation {state.meta.generation >= 0 ? state.meta.generation : '—'}
      </span>
    </div>
  );
}
