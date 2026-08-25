import { useIsr } from '@/presentation/hooks/useIsr';
import type { ISRObservation } from '@esap/observation-client';

function Unavailable({ detail }: { detail?: string }): JSX.Element {
  return (
    <div className="rounded border border-dashed border-slate-300 bg-white p-4 text-sm text-slate-500">
      ISR observation unavailable{detail ? ` — ${detail}` : ''}. The platform returns 503 until
      the CanonicalIsrAccessor binding is live; no substitute data is shown.
    </div>
  );
}

export function IsrPanel({ observation }: { observation?: ISRObservation }): JSX.Element {
  const query = useIsr();
  if (observation === undefined && query.isLoading) {
    return <div className="p-4 text-sm text-slate-500">Loading ISR…</div>;
  }
  if (observation === undefined) return <Unavailable detail={query.error?.message} />;

  const isr = observation;
  return (
    <div className="space-y-4" data-testid="isr-panel">
      <div className="text-xs text-slate-500">ISR revision: {isr.isrRevision}</div>
      <section>
        <h3 className="mb-2 text-sm font-semibold">Domains</h3>
        <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {isr.domains.map((d) => (
            <li key={d.name} className="rounded border border-slate-200 bg-white p-3 text-sm">
              <span className="font-medium">{d.name}</span>
              <span className="ml-2 text-slate-500">{d.capabilityCount} capabilities</span>
            </li>
          ))}
        </ul>
      </section>
      <section>
        <h3 className="mb-2 text-sm font-semibold">Services</h3>
        <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {isr.services.map((s) => (
            <li key={s.id} className="rounded border border-slate-200 bg-white p-3 text-sm">
              <span className="font-medium">{s.name}</span>
              <span className="ml-2 text-slate-500">{s.domain}</span>
            </li>
          ))}
        </ul>
      </section>
      <section>
        <h3 className="mb-2 text-sm font-semibold">Deployment targets</h3>
        <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {isr.deploymentTargets.map((t) => (
            <li key={t.target} className="rounded border border-slate-200 bg-white p-3 text-sm">
              <span className="font-medium">{t.target}</span>
              <span className="ml-2 text-slate-500">{t.serviceCount} services</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

export { Unavailable as IsrUnavailable };
