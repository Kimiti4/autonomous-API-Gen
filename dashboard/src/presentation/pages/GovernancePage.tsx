import { useState } from 'react';
import { Header } from '@/presentation/components/Layout';
import { useProjection } from '@/presentation/hooks/useProjection';
import { useGovernance } from '@/presentation/hooks/useGovernance';
import { GovernancePanel } from '@/presentation/components/GovernancePanel';

export function GovernancePage(): JSX.Element {
  const { state } = useProjection();
  const [input, setInput] = useState('');
  const [candidateId, setCandidateId] = useState<string | null>(null);
  const query = useGovernance(candidateId);

  const facetCandidate =
    (state.facets.governance?.[0] as { candidateId?: string } | undefined)?.candidateId ?? null;

  return (
    <>
      <Header title="Governance" />
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
              placeholder={facetCandidate ?? 'e.g. cand-001'}
            />
          </label>
          <button type="submit" className="rounded bg-brand-500 px-3 py-1.5 text-sm text-white">
            Fetch projection
          </button>
        </form>
        {query.isLoading && candidateId !== null && (
          <div className="text-sm text-slate-500">Loading governance…</div>
        )}
        {query.error && (
          <div className="rounded border border-dashed border-red-300 bg-red-50 p-4 text-sm text-red-800">
            Governance projection unavailable — {query.error.message}
          </div>
        )}
        {query.data && <GovernancePanel projection={query.data} />}
      </div>
    </>
  );
}
