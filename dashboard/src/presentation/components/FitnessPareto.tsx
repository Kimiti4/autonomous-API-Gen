import type { FitnessReport } from '@esap/observation-client';

/**
 * Renders the platform's authoritative Pareto report. The dashboard is
 * FORBIDDEN from recomputing isOnParetoFrontier (platform invariant).
 */
export function FitnessPareto({ report }: { report: FitnessReport }): JSX.Element {
  const dims = report.objectives.map((o) => o.dimension);
  return (
    <div className="space-y-4" data-testid="fitness-pareto">
      <div className="text-xs text-slate-500">
        Generation {report.generation} · evaluated {report.evaluatedAt}
      </div>
      <section>
        <h3 className="mb-2 text-sm font-semibold">Objectives</h3>
        <ul className="flex flex-wrap gap-2">
          {report.objectives.map((o) => (
            <li key={o.dimension} className="rounded bg-slate-100 px-2 py-1 text-xs">
              {o.dimension} · {o.direction} · {o.normalization}
            </li>
          ))}
        </ul>
      </section>
      <table className="w-full border-collapse text-sm" data-testid="fitness-table">
        <thead>
          <tr className="border-b border-slate-200 text-left text-xs uppercase text-slate-500">
            <th className="py-2 pr-4">Candidate</th>
            {dims.map((d) => (
              <th key={d} className="py-2 pr-4">{d}</th>
            ))}
            <th className="py-2">Pareto frontier</th>
          </tr>
        </thead>
        <tbody>
          {report.candidates.map((c) => (
            <tr
              key={c.candidateId}
              className={`border-b border-slate-100 ${c.isOnParetoFrontier ? 'bg-emerald-50' : ''}`}
            >
              <td className="py-2 pr-4 font-medium">{c.candidateId}</td>
              {dims.map((d) => (
                <td key={d} className="py-2 pr-4 tabular-nums">
                  {c.scores[d] ?? '—'}
                </td>
              ))}
              <td className="py-2">
                {c.isOnParetoFrontier ? (
                  <span className="rounded bg-emerald-600 px-2 py-0.5 text-xs text-white">yes</span>
                ) : (
                  <span className="text-slate-400">no</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
