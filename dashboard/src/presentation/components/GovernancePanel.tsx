import type {
  CandidateGovernanceProjection,
  GovernanceDecision,
} from '@esap/observation-client';

/**
 * Renders governance data exactly as the platform publishes it.
 * Deviation note vs. earlier UI mockups: the frozen GovernanceProjection
 * contract exposes decision.fromState/toState as strings, a boolean
 * authorizesTransition flag, and gate ids only — richer fields are NOT
 * invented here.
 */
export function GovernancePanel({
  projection,
}: {
  projection: CandidateGovernanceProjection;
}): JSX.Element {
  return (
    <div className="space-y-4" data-testid="governance-panel">
      <section>
        <h3 className="mb-2 text-sm font-semibold">Decisions</h3>
        {projection.decisions.length === 0 && (
          <div className="text-sm text-slate-500">No recorded decisions.</div>
        )}
        <ul className="space-y-2">
          {projection.decisions.map((d) => (
            <DecisionRow key={d.decisionId} decision={d} />
          ))}
        </ul>
      </section>
    </div>
  );
}

function DecisionRow({ decision }: { decision: GovernanceDecision }): JSX.Element {
  return (
    <li className="rounded border border-slate-200 bg-white p-3 text-sm">
      <div className="flex items-center gap-2">
        <span className="rounded bg-brand-500 px-2 py-0.5 text-xs text-white">
          {decision.verdict}
        </span>
        <span className="font-medium">{decision.candidateId}</span>
        <span className="text-xs text-slate-500">gen {decision.generation}</span>
        {decision.authorizesTransition ? (
          <span className="text-xs text-emerald-700">
            {decision.fromState} → {decision.toState} (authorized)
          </span>
        ) : (
          <span className="text-xs text-slate-500">no transition authorized</span>
        )}
      </div>
      <p className="mt-1 text-slate-700">{decision.rationale}</p>
      <div className="mt-1 text-xs text-slate-400">
        decided by {decision.decidedBy.join(', ')} · {decision.decidedAt}
        {decision.supersedesDecisionId !== null &&
          ` · supersedes ${decision.supersedesDecisionId}`}
      </div>
    </li>
  );
}
