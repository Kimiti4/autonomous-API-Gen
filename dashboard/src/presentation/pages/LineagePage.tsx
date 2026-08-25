import { useState } from 'react';
import { Header } from '@/presentation/components/Layout';
import { useLineage } from '@/presentation/hooks/useLineage';
import { useEvidence } from '@/presentation/hooks/useEvidence';
import { LineageExplorer } from '@/presentation/components/LineageExplorer';

export function LineagePage(): JSX.Element {
  const [input, setInput] = useState('');
  const [candidateId, setCandidateId] = useState<string | null>(null);
  const query = useLineage(candidateId);
  const firstEvidenceId =
    query.data?.verifications[0]?.evidenceRefs[0] ?? null;
  const evidence = useEvidence(firstEvidenceId);

  return (
    <>
      <Header title="Candidate Lineage" />
      <div className="space-y-6 p-6">
        <form
          className="flex items-end gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            setCandidateId(input.trim() === '' ? null : input.trim());
          }}
        >
          <label className="text-sm">
            <span className="block text-slate-600">Candidate ID</span>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              className="mt-1 w-64 rounded border border-slate-300 px-2 py-1"
              placeholder="e.g. cand-001"
            />
          </label>
          <button type="submit" className="rounded bg-brand-500 px-3 py-1.5 text-sm text-white">
            Trace lineage
          </button>
        </form>
        {query.isLoading && candidateId !== null && (
          <div className="text-sm text-slate-500">Loading lineage…</div>
        )}
        {query.error && (
          <div className="rounded border border-dashed border-red-300 bg-red-50 p-4 text-sm text-red-800">
            Lineage unavailable — {query.error.message}
          </div>
        )}
        {query.data && <LineageExplorer lineage={query.data} />}
        {evidence.data && (
          <div className="text-xs text-slate-500" data-testid="evidence-ref">
            Evidence {evidence.data.evidenceId} · sha256:{evidence.data.contentHash.slice(0, 16)}…
          </div>
        )}
      </div>
    </>
  );
}
