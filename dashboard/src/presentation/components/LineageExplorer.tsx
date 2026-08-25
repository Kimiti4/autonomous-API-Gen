import type { CandidateLineage } from '@esap/observation-client';

/**
 * Renders candidate lineage exactly as the platform publishes it:
 * requirementIds, origin spec, and chronological operation / evaluation /
 * verification / deployment / feedback lists.
 */
export function LineageExplorer({ lineage }: { lineage: CandidateLineage }): JSX.Element {
  return (
    <div className="space-y-4" data-testid="lineage-explorer">
      <div className="text-xs text-slate-500">
        {lineage.candidateId} · gen {lineage.generation} · ISR {lineage.isrRevision}
      </div>

      <section>
        <h3 className="mb-2 text-sm font-semibold">Origin</h3>
        {lineage.origin === null ? (
          <div className="text-sm text-slate-500">No origin recorded.</div>
        ) : (
          <div className="rounded border border-slate-200 bg-white p-3 text-sm">
            <span className="font-medium">{lineage.origin.operationType}</span>
            {lineage.origin.parentCandidateIds.length > 0 && (
              <span className="ml-2 text-slate-500">
                parents: {lineage.origin.parentCandidateIds.join(', ')}
              </span>
            )}
            <p className="mt-1 text-slate-700">{lineage.origin.summary}</p>
          </div>
        )}
      </section>

      <section>
        <h3 className="mb-2 text-sm font-semibold">Requirements</h3>
        <ul className="flex flex-wrap gap-2">
          {lineage.requirementIds.map((r) => (
            <li key={r} className="rounded bg-slate-100 px-2 py-1 text-xs">{r}</li>
          ))}
        </ul>
      </section>

      <Timeline lineage={lineage} />
    </div>
  );
}

function Timeline({ lineage }: { lineage: CandidateLineage }): JSX.Element {
  const rows: Array<{ kind: string; id: string; detail: string; at: string }> = [
    ...lineage.operations.map((o) => ({
      kind: 'operation',
      id: o.operationId,
      detail: `${o.operationType} — ${o.summary}`,
      at: o.occurredAt,
    })),
    ...lineage.evaluations.map((e) => ({
      kind: 'evaluation',
      id: e.evaluationId,
      detail: `gen ${e.generation} score ${e.fitnessScore}`,
      at: e.evaluatedAt,
    })),
    ...lineage.verifications.map((v) => ({
      kind: 'verification',
      id: v.verificationId,
      detail: `${v.verifiedBy} → ${v.verdict}`,
      at: v.verifiedAt,
    })),
    ...lineage.deployments.map((d) => ({
      kind: 'deployment',
      id: d.deploymentId,
      detail: `${d.target} by ${d.deployedBy}`,
      at: d.deployedAt,
    })),
    ...lineage.feedback.map((f) => ({
      kind: 'feedback',
      id: f.feedbackId,
      detail: `${f.source} — ${f.summary}${f.influencedNextGeneration ? ' (influenced next gen)' : ''}`,
      at: f.receivedAt,
    })),
  ].sort((a, b) => a.at.localeCompare(b.at));

  return (
    <section>
      <h3 className="mb-2 text-sm font-semibold">History</h3>
      <ol className="space-y-2">
        {rows.map((row) => (
          <li key={`${row.kind}-${row.id}`} className="rounded border border-slate-200 bg-white p-3 text-sm">
            <div className="flex items-center gap-2">
              <span className="rounded bg-slate-800 px-2 py-0.5 text-xs capitalize text-white">
                {row.kind}
              </span>
              <span className="text-xs text-slate-400">{row.at}</span>
            </div>
            <div className="mt-1 text-slate-700">{row.detail}</div>
          </li>
        ))}
      </ol>
    </section>
  );
}
