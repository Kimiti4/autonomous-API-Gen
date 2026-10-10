import { useObservationFetch } from '@/presentation/hooks/useObservationFetch';

type DeliveryStatus = 'pending' | 'delivering' | 'delivered' | 'dead_letter';

interface MaintenanceOutboxItem {
  event_digest: string;
  status: DeliveryStatus;
  attempts: number;
  next_attempt_at: number;
  lease_until: number | null;
  observatory_event_id: string | null;
  last_error: string | null;
  created_at: number;
  updated_at: number;
}

interface MaintenanceOutboxStatus {
  status: 'available';
  summary: Record<DeliveryStatus, number>;
  items: MaintenanceOutboxItem[];
}

const STATUS_STYLE: Record<DeliveryStatus, string> = {
  pending: 'bg-amber-100 text-amber-800',
  delivering: 'bg-sky-100 text-sky-800',
  delivered: 'bg-emerald-100 text-emerald-800',
  dead_letter: 'bg-rose-100 text-rose-800',
};

function formatTimestamp(value: number): string {
  if (!Number.isFinite(value) || value <= 0) return 'Not recorded';
  return new Date(value * 1000).toLocaleString();
}

export function MaintenanceOutboxPanel(): JSX.Element {
  const query = useObservationFetch<MaintenanceOutboxStatus>('/maintenance-outbox');

  return (
    <section className="space-y-4 rounded-lg border border-slate-200 bg-white p-5" aria-labelledby="maintenance-outbox-title" data-testid="maintenance-outbox-panel">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="maintenance-outbox-title" className="text-base font-semibold text-slate-900">
            Governed maintenance delivery
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Evidence-delivery queue status. This view is read-only; it does not authorize repairs or production changes.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void query.refetch()}
          disabled={query.isFetching}
          className="rounded border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
        >
          {query.isFetching ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>

      {query.isLoading && <p role="status" className="text-sm text-slate-500">Loading maintenance delivery status…</p>}

      {query.error && (
        <div role="status" className="rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          Maintenance delivery status is unavailable. {query.error.message === '503'
            ? 'The outbox may not be configured or its storage may be unavailable.'
            : query.error.message}
          No delivery state is inferred while the status endpoint is unavailable.
        </div>
      )}

      {query.data && (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {(['pending', 'delivering', 'delivered', 'dead_letter'] as DeliveryStatus[]).map((status) => (
              <div key={status} className="rounded border border-slate-200 p-3">
                <div className="text-xs uppercase tracking-wide text-slate-500">{status.replace('_', ' ')}</div>
                <div className="mt-1 text-2xl font-semibold tabular-nums text-slate-900">
                  {query.data.summary[status] ?? 0}
                </div>
              </div>
            ))}
          </div>

          <div>
            <h3 className="mb-2 text-sm font-semibold text-slate-800">Recently updated events</h3>
            {query.data.items.length === 0 ? (
              <p className="text-sm text-slate-500">No maintenance events have been queued.</p>
            ) : (
              <ul className="divide-y divide-slate-100">
                {query.data.items.map((item) => (
                  <li key={item.event_digest} className="flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between">
                    <div className="min-w-0">
                      <code className="block truncate text-xs text-slate-600" title={item.event_digest}>
                        {item.event_digest}
                      </code>
                      <p className="mt-1 text-xs text-slate-500">
                        Attempts: {item.attempts} · Updated: {formatTimestamp(item.updated_at)}
                      </p>
                      {item.last_error && <p className="mt-1 text-xs text-rose-700">Last failure: {item.last_error}</p>}
                      {item.observatory_event_id && <p className="mt-1 text-xs text-emerald-700">Acknowledged event: {item.observatory_event_id}</p>}
                    </div>
                    <span className={`w-fit rounded px-2 py-1 text-xs font-medium ${STATUS_STYLE[item.status] ?? 'bg-slate-100 text-slate-700'}`}>
                      {item.status.replace('_', ' ')}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </>
      )}
    </section>
  );
}
