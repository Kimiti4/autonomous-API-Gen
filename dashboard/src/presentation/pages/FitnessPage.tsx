import { useState } from 'react';
import { Header, StatCard } from '@/presentation/components/Layout';
import { useProjection } from '@/presentation/hooks/useProjection';
import { useFitness } from '@/presentation/hooks/useFitness';
import { FitnessPareto } from '@/presentation/components/FitnessPareto';

export function FitnessPage(): JSX.Element {
  const { state } = useProjection();
  const [input, setInput] = useState('');
  const [requested, setRequested] = useState<number | null>(null);
  const query = useFitness(requested);

  return (
    <>
      <Header title="Fitness" />
      <div className="space-y-6 p-6">
        <StatCard
          label="Current generation (live)"
          value={state.meta.generation >= 0 ? state.meta.generation : '—'}
        />
        <form
          className="flex items-end gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            setRequested(Number.parseInt(input, 10));
          }}
        >
          <label className="text-sm">
            <span className="block text-slate-600">Generation</span>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              inputMode="numeric"
              pattern="[0-9]*"
              className="mt-1 w-32 rounded border border-slate-300 px-2 py-1"
              placeholder="0"
            />
          </label>
          <button type="submit" className="rounded bg-brand-500 px-3 py-1.5 text-sm text-white">
            Fetch report
          </button>
        </form>
        {query.isLoading && requested !== null && (
          <div className="text-sm text-slate-500">Loading report…</div>
        )}
        {query.error && (
          <div className="rounded border border-dashed border-red-300 bg-red-50 p-4 text-sm text-red-800">
            Fitness report unavailable — {query.error.message}
          </div>
        )}
        {query.data && requested !== null && query.data.generation === requested && (
          <FitnessPareto report={query.data} />
        )}
      </div>
    </>
  );
}
