import type { ReactNode } from 'react';
import { NavLink } from 'react-router-dom';
import { ProjectionStatusBanner } from '@/presentation/components/ProjectionStatusBanner';

const NAV = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/isr', label: 'ISR' },
  { to: '/evolution', label: 'Evolution' },
  { to: '/fitness', label: 'Fitness' },
  { to: '/governance', label: 'Governance' },
  { to: '/lineage', label: 'Lineage' },
];

export function Layout({ children }: { children: ReactNode }): JSX.Element {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <ProjectionStatusBanner />
        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </div>
  );
}

export function Sidebar(): JSX.Element {
  return (
    <nav aria-label="Primary" className="w-48 shrink-0 border-r border-slate-200 bg-white p-4">
      <ul className="space-y-1">
        {NAV.map((item) => (
          <li key={item.to}>
            <NavLink
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `block rounded px-3 py-2 text-sm ${
                  isActive ? 'bg-brand-500 text-white' : 'text-slate-700 hover:bg-slate-100'
                }`
              }
            >
              {item.label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}

export function Header({ title }: { title: string }): JSX.Element {
  return (
    <header className="border-b border-slate-200 bg-white px-6 py-4">
      <h1 className="text-lg font-semibold text-slate-900">{title}</h1>
    </header>
  );
}

export function StatCard({
  label,
  value,
}: {
  label: string;
  value: ReactNode;
}): JSX.Element {
  return (
    <div className="rounded border border-slate-200 bg-white p-4" data-testid="stat-card">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-xl font-semibold text-slate-900">{value}</div>
    </div>
  );
}
