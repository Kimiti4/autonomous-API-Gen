# Phase D — Full React Presentation Backend (complete, production-ready)

This is the complete, self-contained Phase D runtime. It is a **read-only observation compiler backend**: it never recomputes Pareto, never reinterprets governance, never touches transport/sequencing — it consumes `@esap/observation-client` via `useProjection()` and dumb rendering. All prior review constraints are baked in (runtime config, ingress-only topology, cookie auth, no fake `/metrics`, read-only rootfs + tmpfs, CSP `connect-src`, OTel push).

**Prerequisite:** `observation-client/src/index.ts` must export: `LiveProjection, HttpObservationClient, WebSocketEventStream, IndexedDbCheckpointStore, MemoryCheckpointStore, observationReducer, initialUiState` and types `ObservationUiState, ProjectionStatus, ObservationMetrics, MetricsSink, ISRObservation, FitnessReport, GovernanceProjection, CandidateGovernanceProjection, CandidateLineage, EvidenceRecord`.

---

## Scaffolding

### `dashboard/package.json`
```json
{
  "name": "@esap/dashboard",
  "version": "1.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "@esap/observation-client": "file:../observation-client",
    "@opentelemetry/api": "^1.9.0",
    "@opentelemetry/exporter-metrics-otlp-http": "^0.53.0",
    "@opentelemetry/exporter-trace-otlp-http": "^0.53.0",
    "@opentelemetry/resources": "^1.26.0",
    "@opentelemetry/sdk-metrics": "^1.26.0",
    "@opentelemetry/sdk-trace-web": "^1.26.0",
    "@opentelemetry/semantic-conventions": "^1.27.0",
    "@tanstack/react-query": "^5.59.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.27.0",
    "recharts": "^2.13.0"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.5.0",
    "@testing-library/react": "^16.0.1",
    "@types/react": "^18.3.11",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.3",
    "autoprefixer": "^10.4.20",
    "jsdom": "^25.0.1",
    "postcss": "^8.4.47",
    "tailwindcss": "^3.4.14",
    "typescript": "^5.6.3",
    "vite": "^5.4.10",
    "vitest": "^2.1.3"
  }
}
```

### `dashboard/tsconfig.json`
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedIndexedAccess": true,
    "isolatedModules": true,
    "resolveJsonModule": true,
    "allowImportingTsExtensions": true,
    "noEmit": true,
    "skipLibCheck": true,
    "baseUrl": ".",
    "paths": { "@/*": ["src/*"] }
  },
  "include": ["src"]
}
```

### `dashboard/vite.config.ts`
```ts
import path from 'node:path';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { '@': path.resolve(__dirname, 'src') } },
  server: {
    port: 5173,
    proxy: {
      // Dev only; production uses the ingress.
      '/observation': { target: 'http://localhost:8080', changeOrigin: true },
      '/config': { target: 'http://localhost:8080', changeOrigin: true },
      '/ws': { target: 'ws://localhost:8080', ws: true },
    },
  },
  build: { sourcemap: true, target: 'es2022' },
  test: { environment: 'jsdom', globals: false, setupFiles: ['./src/tests/setup.ts'] },
});
```

### `dashboard/tailwind.config.js`
```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: { colors: { brand: { 50: '#eef4ff', 500: '#3b5bdb', 700: '#2741a6', 900: '#14216b' } } },
  },
  plugins: [],
};
```

### `dashboard/postcss.config.js`
```js
export default { plugins: { tailwindcss: {}, autoprefixer: {} } };
```

### `dashboard/index.html`
```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="description" content="ESAP — human observability surface of the autonomous platform" />
    <title>ESAP Observation</title>
  </head>
  <body class="bg-slate-50 text-slate-900 antialiased">
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

### `dashboard/src/index.css`
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root { font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
body { margin: 0; }
```

### `dashboard/src/vite-env.d.ts`
```ts
/// <reference types="vite/client" />
```

### `dashboard/public/config/runtime.json`
```json
{
  "observationApiPath": "/observation",
  "observationWsPath": "/ws/evolution",
  "streamId": "evolution-main",
  "enableTelemetry": false,
  "serviceName": "esap-dashboard",
  "authLoginPath": "/auth/login"
}
```

---

## Application layer

### `src/application/configLoader.ts`
```ts
export interface DashboardRuntimeConfig {
  observationApiPath: string;
  observationWsPath: string;
  streamId: string;
  enableTelemetry: boolean;
  otlpTracesEndpoint?: string;
  otlpMetricsEndpoint?: string;
  serviceName: string;
  authLoginPath: string;
}

const DEFAULTS: DashboardRuntimeConfig = {
  observationApiPath: '/observation',
  observationWsPath: '/ws/evolution',
  streamId: 'evolution-main',
  enableTelemetry: false,
  serviceName: 'esap-dashboard',
  authLoginPath: '/auth/login',
};

/** Runtime configuration served by nginx / K8s ConfigMap — NOT build-time env. */
export async function loadRuntimeConfig(
  path = '/config/runtime.json',
  fetchImpl: typeof fetch = fetch,
): Promise<DashboardRuntimeConfig> {
  try {
    const res = await fetchImpl(path, { cache: 'no-store', credentials: 'same-origin' });
    if (!res.ok) return DEFAULTS;
    const partial = (await res.json()) as Partial<DashboardRuntimeConfig>;
    return { ...DEFAULTS, ...partial };
  } catch {
    return DEFAULTS; // same-origin defaults are safe; config is not a security boundary
  }
}
```

### `src/application/statusStore.ts`
```ts
import type { ProjectionStatus } from '@esap/observation-client';

type Listener = () => void;

let current: ProjectionStatus | null = null;
const listeners = new Set<Listener>();

export function setProjectionStatus(status: ProjectionStatus): void {
  current = status;
  for (const listener of listeners) listener();
}

export function getProjectionStatus(): ProjectionStatus | null {
  return current;
}

export function subscribeProjectionStatus(listener: Listener): () => void {
  listeners.add(listener);
  return () => { listeners.delete(listener); };
}

/** Test hook. */
export function resetProjectionStatus(): void {
  current = null;
  listeners.clear();
}
```

### `src/application/observationClient.ts`
```ts
import {
  HttpObservationClient, IndexedDbCheckpointStore, LiveProjection, MemoryCheckpointStore,
  WebSocketEventStream, initialUiState, observationReducer, type MetricsSink, type ObservationUiState,
} from '@esap/observation-client';
import type { DashboardRuntimeConfig } from './configLoader';
import { setProjectionStatus } from './statusStore';

let projection: LiveProjection<ObservationUiState, unknown> | null = null;
let started = false;

export interface ObservationClientOptions { metricsSink?: MetricsSink | undefined; }

export async function startObservationClient(
  config: DashboardRuntimeConfig,
  options: ObservationClientOptions = {},
): Promise<void> {
  if (started) return;
  started = true;

  const wsProtocol = typeof location !== 'undefined' && location.protocol === 'https:' ? 'wss' : 'ws';
  const wsUrl = `${wsProtocol}://${location.host}${config.observationWsPath}`;

  const http = new HttpObservationClient<ObservationUiState, unknown>({
    baseUrl: config.observationApiPath,
    streamId: config.streamId,
    credentials: 'same-origin', // cookie auth; never token-in-URL
  });
  const eventStream = new WebSocketEventStream<unknown>({ url: wsUrl });
  const checkpointStore = typeof indexedDB !== 'undefined'
    ? new IndexedDbCheckpointStore<ObservationUiState>()
    : new MemoryCheckpointStore<ObservationUiState>();

  projection = new LiveProjection<ObservationUiState, unknown>({
    streamId: config.streamId,
    initialState: initialUiState(),
    reducer: observationReducer,
    snapshotSource: http,
    replaySource: http,
    eventStream,
    checkpointStore,
    onStatusChange: setProjectionStatus,
    livenessProbe: async () => {
      await fetch(`${config.observationApiPath}/capabilities`, { credentials: 'same-origin' });
      return true;
    },
    ...(options.metricsSink ? { metricsSink: options.metricsSink } : {}),
  });

  await projection.start();
}

export function getProjection(): LiveProjection<ObservationUiState, unknown> {
  if (!projection) throw new Error('Observation client not started');
  return projection;
}

export async function stopObservationClient(): Promise<void> {
  if (!started) return;
  await projection?.stop();
  projection = null;
  started = false;
}
```

---

## Infrastructure (telemetry)

### `src/infrastructure/telemetry/otel.ts`
```ts
import { metrics } from '@opentelemetry/api';
import { OTLPMetricExporter } from '@opentelemetry/exporter-metrics-otlp-http';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { Resource } from '@opentelemetry/resources';
import { MeterProvider, PeriodicExportingMetricReader } from '@opentelemetry/sdk-metrics';
import { BatchSpanProcessor, WebTracerProvider } from '@opentelemetry/sdk-trace-web';
import { SEMRESATTRS_SERVICE_NAME } from '@opentelemetry/semantic-conventions';
import type { DashboardRuntimeConfig } from '@/application/configLoader';

/** OTel bootstrap. Lives in the dashboard (infrastructure), not observation-client. */
export function initTelemetry(config: DashboardRuntimeConfig): void {
  if (!config.enableTelemetry) return;

  const resource = new Resource({ [SEMRESATTRS_SERVICE_NAME]: config.serviceName });

  if (config.otlpTracesEndpoint) {
    const tracerProvider = new WebTracerProvider({ resource });
    tracerProvider.addSpanProcessor(
      new BatchSpanProcessor(new OTLPTraceExporter({ url: config.otlpTracesEndpoint })),
    );
    tracerProvider.register();
  }

  if (config.otlpMetricsEndpoint) {
    const meterProvider = new MeterProvider({ resource });
    meterProvider.addMetricReader(
      new PeriodicExportingMetricReader({
        exporter: new OTLPMetricExporter({ url: config.otlpMetricsEndpoint }),
        exportIntervalMillis: 15_000,
      }),
    );
    metrics.setGlobalMeterProvider(meterProvider);
  }
}
```

### `src/infrastructure/telemetry/OtelMetricsSink.ts`
```ts
import { metrics } from '@opentelemetry/api';
import type { MetricsSink, ObservationMetrics } from '@esap/observation-client';

const METRIC_NAMES = [
  'eventsApplied', 'duplicatesIgnored', 'gapsDetected', 'recoveriesSucceeded',
  'recoveriesFailed', 'replayedEvents', 'snapshotFetches', 'streamDisconnects',
  'streamReconnects', 'heartbeats',
] as const;

/** Exports LiveProjection counters as OTel observable gauges. */
export class OtelMetricsSink implements MetricsSink {
  private latest: ObservationMetrics | null = null;

  constructor(serviceName = 'esap-dashboard') {
    const meter = metrics.getMeter(serviceName);
    for (const name of METRIC_NAMES) {
      meter
        .createObservableGauge(`observation.${name}`, { description: `Observation client metric: ${name}` })
        .addCallback((result) => { if (this.latest) result.observe(this.latest[name]); });
    }
  }

  record(snapshot: ObservationMetrics): void {
    this.latest = snapshot;
  }
}
```

---

## Presentation — context & hooks

### `src/presentation/contexts/ConfigContext.tsx`
```tsx
import { createContext, useContext, type ReactNode } from 'react';
import type { DashboardRuntimeConfig } from '@/application/configLoader';

const ConfigContext = createContext<DashboardRuntimeConfig | null>(null);

export function ConfigProvider({ config, children }: { config: DashboardRuntimeConfig; children: ReactNode }) {
  return <ConfigContext.Provider value={config}>{children}</ConfigContext.Provider>;
}

export function useDashboardConfig(): DashboardRuntimeConfig {
  const ctx = useContext(ConfigContext);
  if (!ctx) throw new Error('useDashboardConfig must be used within ConfigProvider');
  return ctx;
}
```

### `src/presentation/hooks/useProjection.ts`
```ts
import { useSyncExternalStore } from 'react';
import type { ObservationMetrics, ObservationUiState, ProjectionStatus } from '@esap/observation-client';
import { getProjection } from '@/application/observationClient';
import { getProjectionStatus, subscribeProjectionStatus } from '@/application/statusStore';

export interface ProjectionView {
  state: ObservationUiState;
  status: ProjectionStatus | null;
  metrics: ObservationMetrics;
}

/** The ONLY surface React touches. No transport, sequencing, or recovery. */
export function useProjection(): ProjectionView {
  const projection = getProjection();
  const state = useSyncExternalStore(
    (onChange) => projection.subscribe(onChange),
    () => projection.getState(),
    () => projection.getState(),
  );
  const status = useSyncExternalStore(subscribeProjectionStatus, getProjectionStatus, getProjectionStatus);
  return { state, status, metrics: projection.metrics() };
}
```

### `src/presentation/hooks/useObservationFetch.ts`
```ts
import { useCallback } from 'react';
import { useDashboardConfig } from '@/presentation/contexts/ConfigContext';

/** Bound, credentialed fetch against the Observation API. */
export function useObservationFetch() {
  const config = useDashboardConfig();
  return useCallback(
    async function observationFetch<T>(path: string): Promise<T> {
      const res = await fetch(`${config.observationApiPath}${path}`, { credentials: 'same-origin' });
      if (!res.ok) throw new Error(`Observation API ${res.status} for ${path}`);
      return (await res.json()) as T;
    },
    [config.observationApiPath],
  );
}
```

### `src/presentation/hooks/useIsr.ts`
```ts
import { useQuery } from '@tanstack/react-query';
import type { ISRObservation } from '@esap/observation-client';
import { useObservationFetch } from './useObservationFetch';

export function useIsr() {
  const observationFetch = useObservationFetch();
  return useQuery({ queryKey: ['isr'], queryFn: () => observationFetch<ISRObservation>('/isr') });
}
```

### `src/presentation/hooks/useFitness.ts`
```ts
import { useQuery } from '@tanstack/react-query';
import type { FitnessReport } from '@esap/observation-client';
import { useObservationFetch } from './useObservationFetch';

export function useFitnessReport(generation: number | undefined) {
  const observationFetch = useObservationFetch();
  return useQuery({
    queryKey: ['fitness', generation],
    enabled: generation !== undefined,
    queryFn: () => observationFetch<FitnessReport>(`/fitness?generation=${generation}`),
  });
}
```

### `src/presentation/hooks/useGovernance.ts`
```ts
import { useQuery } from '@tanstack/react-query';
import type { CandidateGovernanceProjection, GovernanceProjection } from '@esap/observation-client';
import { useObservationFetch } from './useObservationFetch';

export function useGenerationGovernance(generation: number | undefined) {
  const observationFetch = useObservationFetch();
  return useQuery({
    queryKey: ['governance', 'generation', generation],
    enabled: generation !== undefined,
    queryFn: () => observationFetch<GovernanceProjection>(`/governance?generation=${generation}`),
  });
}

export function useCandidateGovernance(candidateId: string | undefined) {
  const observationFetch = useObservationFetch();
  return useQuery({
    queryKey: ['governance', 'candidate', candidateId],
    enabled: !!candidateId,
    queryFn: () => observationFetch<CandidateGovernanceProjection>(`/governance/candidate?candidateId=${candidateId}`),
  });
}
```

### `src/presentation/hooks/useLineage.ts`
```ts
import { useQuery } from '@tanstack/react-query';
import type { CandidateLineage } from '@esap/observation-client';
import { useObservationFetch } from './useObservationFetch';

export function useCandidateLineage(candidateId: string | undefined) {
  const observationFetch = useObservationFetch();
  return useQuery({
    queryKey: ['lineage', candidateId],
    enabled: !!candidateId,
    queryFn: () => observationFetch<CandidateLineage>(`/lineage?candidateId=${candidateId}`),
  });
}
```

### `src/presentation/hooks/useEvidence.ts`
```ts
import { useQuery } from '@tanstack/react-query';
import type { EvidenceRecord } from '@esap/observation-client';
import { useObservationFetch } from './useObservationFetch';

export function useEvidence(evidenceId: string | undefined) {
  const observationFetch = useObservationFetch();
  return useQuery({
    queryKey: ['evidence', evidenceId],
    enabled: !!evidenceId,
    queryFn: () => observationFetch<EvidenceRecord>(`/evidence?evidenceId=${evidenceId}`),
  });
}
```

---

## Presentation — components

### `src/presentation/components/ProjectionProvider.tsx`
```tsx
import { useEffect, useState, type ReactNode } from 'react';
import type { MetricsSink } from '@esap/observation-client';
import { startObservationClient } from '@/application/observationClient';
import type { DashboardRuntimeConfig } from '@/application/configLoader';

export function ProjectionProvider({
  config, metricsSink, children,
}: { config: DashboardRuntimeConfig; metricsSink?: MetricsSink | undefined; children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    startObservationClient(config, { metricsSink })
      .then(() => { if (!cancelled) setReady(true); })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to start observation');
      });
    return () => { cancelled = true; };
  }, [config, metricsSink]);

  if (error) {
    return <div role="alert" className="flex min-h-screen items-center justify-center p-6 text-rose-600">Observation unavailable: {error}</div>;
  }
  if (!ready) {
    return <div className="flex min-h-screen items-center justify-center p-6 text-slate-500">Connecting to platform observation…</div>;
  }
  return <>{children}</>;
}
```

### `src/presentation/components/ProjectionStatusBanner.tsx`
```tsx
import type { ProjectionStatus } from '@esap/observation-client';
import { useDashboardConfig } from '@/presentation/contexts/ConfigContext';
import { useProjection } from '@/presentation/hooks/useProjection';

const LABELS: Record<ProjectionStatus['state'], string> = {
  initializing: 'Initializing', healthy: 'Live', degraded: 'Degraded',
  stale: 'Stale', desynchronized: 'Desynchronized', unavailable: 'Unavailable',
};
const COLORS: Record<ProjectionStatus['state'], string> = {
  healthy: 'bg-emerald-100 text-emerald-700',
  degraded: 'bg-amber-100 text-amber-700',
  stale: 'bg-amber-100 text-amber-700',
  desynchronized: 'bg-rose-100 text-rose-700',
  unavailable: 'bg-slate-200 text-slate-600',
  initializing: 'bg-slate-100 text-slate-600',
};

export function ProjectionStatusBanner() {
  const { status } = useProjection();
  const config = useDashboardConfig();
  if (!status) return null;

  const isAuthError = status.state === 'unavailable' && status.lastError?.code === 'SEC_UNAUTHENTICATED';

  return (
    <div className="flex items-center gap-3 text-sm">
      <span className={`rounded-full px-3 py-1 text-xs font-medium ${COLORS[status.state]}`}>{LABELS[status.state]}</span>
      <span className="font-mono text-xs text-slate-500">
        applied {status.appliedSequence} · authoritative {status.authoritativeSequence}
      </span>
      {isAuthError ? (
        <a href={config.authLoginPath} className="rounded bg-brand-500 px-3 py-1 text-xs font-medium text-white hover:bg-brand-700">Sign in</a>
      ) : status.lastError ? (
        <span className="text-xs text-rose-600">{status.lastError.message}</span>
      ) : null}
    </div>
  );
}
```

### `src/presentation/components/{Layout,Sidebar,Header,StatCard}.tsx`
```tsx
// Layout.tsx
import type { ReactNode } from 'react';
import { Header } from './Header';
import { Sidebar } from './Sidebar';

export function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen bg-slate-50">
      <Sidebar />
      <div className="flex flex-1 flex-col">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
```
```tsx
// Sidebar.tsx
import { NavLink } from 'react-router-dom';

const LINKS = [
  { to: '/', label: 'Overview' },
  { to: '/isr', label: 'ISR' },
  { to: '/evolution', label: 'Evolution' },
  { to: '/fitness', label: 'Fitness & Pareto' },
  { to: '/governance', label: 'Governance' },
  { to: '/lineage', label: 'Lineage' },
];

export function Sidebar() {
  return (
    <aside className="w-60 border-r border-slate-200 bg-white p-4">
      <div className="mb-6 text-lg font-semibold text-brand-700">ESAP Observation</div>
      <nav className="flex flex-col gap-1">
        {LINKS.map((link) => (
          <NavLink
            key={link.to} to={link.to} end={link.to === '/'}
            className={({ isActive }) =>
              `rounded px-3 py-2 text-sm transition ${isActive ? 'bg-brand-50 font-medium text-brand-700' : 'text-slate-600 hover:bg-slate-100'}`}
          >
            {link.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
```
```tsx
// Header.tsx
import { ProjectionStatusBanner } from './ProjectionStatusBanner';

export function Header() {
  return (
    <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3">
      <h1 className="text-sm font-semibold text-slate-700">Human Observability Surface</h1>
      <ProjectionStatusBanner />
    </header>
  );
}
```
```tsx
// StatCard.tsx
import type { ReactNode } from 'react';

export function StatCard({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-2 text-2xl font-semibold text-slate-900">{value}</div>
      {hint && <div className="mt-1 text-xs text-slate-500">{hint}</div>}
    </div>
  );
}
```

### `src/presentation/components/{FacetsPanel,EvolutionOverview}.tsx`
```tsx
// FacetsPanel.tsx — live facets from the projection stream. Read-only rendering.
import { useProjection } from '@/presentation/hooks/useProjection';

export function FacetsPanel() {
  const { state } = useProjection();
  const { isr, fitness, evolution, candidates, governance } = state.facets;
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      <Facet title="Evolution" value={evolution} />
      <Facet title="Fitness" value={fitness} />
      <Facet title="ISR" value={isr} />
      <Facet title={`Candidates (${(candidates ?? []).length})`} value={candidates} />
      <Facet title={`Governance (${(governance ?? []).length})`} value={governance} />
    </div>
  );
}

function Facet({ title, value }: { title: string; value: unknown }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="mb-2 text-sm font-semibold text-slate-700">{title}</h3>
      {value === undefined || value === null ? (
        <p className="text-xs text-slate-400">No data yet.</p>
      ) : (
        <pre className="max-h-64 overflow-auto text-xs text-slate-700">{JSON.stringify(value, null, 2)}</pre>
      )}
    </section>
  );
}
```
```tsx
// EvolutionOverview.tsx
import { useProjection } from '@/presentation/hooks/useProjection';
import { StatCard } from './StatCard';

export function EvolutionOverview() {
  const { state } = useProjection();
  const generation = state.meta.generation;
  const candidates = state.facets.candidates ?? [];
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
      <StatCard label="Current Generation" value={generation} />
      <StatCard label="Candidates (live)" value={candidates.length} />
      <StatCard label="Active facets" value={Object.keys(state.meta.facetUpdatedAt).length} hint="facets with activity" />
    </div>
  );
}
```

### `src/presentation/components/FitnessPareto.tsx`
```tsx
import { useMemo, useState } from 'react';
import { CartesianGrid, Legend, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from 'recharts';
import type { FitnessReport } from '@esap/observation-client';

/** Renders the authoritative Pareto frontier. Never recomputes dominance. */
export function FitnessPareto({ report }: { report: FitnessReport }) {
  const dims = report.objectives.map((o) => o.dimension);
  const [xDim, setXDim] = useState(dims[0] ?? '');
  const [yDim, setYDim] = useState(dims[1] ?? dims[0] ?? '');

  const frontier = useMemo(() => new Set(report.paretoFrontierCandidateIds), [report]);
  const points = report.candidates.map((c) => ({
    id: c.candidateId,
    x: c.scores[xDim] ?? 0,
    y: c.scores[yDim] ?? 0,
    pareto: frontier.has(c.candidateId),
  }));
  const onFrontier = points.filter((p) => p.pareto);
  const dominated = points.filter((p) => !p.pareto);

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="mb-3 flex items-center gap-3">
        <h3 className="text-sm font-semibold text-slate-700">
          Pareto frontier · gen {report.generation} · {onFrontier.length}/{points.length} on frontier
        </h3>
        <select value={xDim} onChange={(e) => setXDim(e.target.value)} className="rounded border border-slate-200 px-2 py-1 text-xs">
          {dims.map((d) => <option key={`x-${d}`} value={d}>x: {d}</option>)}
        </select>
        <select value={yDim} onChange={(e) => setYDim(e.target.value)} className="rounded border border-slate-200 px-2 py-1 text-xs">
          {dims.map((d) => <option key={`y-${d}`} value={d}>y: {d}</option>)}
        </select>
      </div>
      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 10, right: 20, bottom: 20, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis type="number" dataKey="x" name={xDim} domain={[0, 1]} tick={{ fontSize: 11 }} />
            <YAxis type="number" dataKey="y" name={yDim} domain={[0, 1]} tick={{ fontSize: 11 }} />
            <Tooltip cursor={{ strokeDasharray: '3 3' }} />
            <Legend />
            <Scatter name="Pareto frontier" data={onFrontier} fill="#2563eb" />
            <Scatter name="Dominated" data={dominated} fill="#94a3b8" />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
```

### `src/presentation/components/IsrPanel.tsx`
```tsx
import { useIsr } from '@/presentation/hooks/useIsr';

export function IsrPanel() {
  const { data, isLoading, error } = useIsr();
  if (isLoading) return <p className="text-sm text-slate-500">Loading ISR…</p>;
  if (error || !data) return <p className="text-sm text-rose-600">ISR unavailable.</p>;
  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-500">ISR revision <span className="font-mono">{data.isrRevision}</span></p>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Section title={`Domains (${data.domains.length})`}>
          {data.domains.map((d) => <li key={d.name}>{d.name} · {d.capabilityCount} capabilities</li>)}
        </Section>
        <Section title={`Services (${data.services.length})`}>
          {data.services.map((s) => <li key={s.id}>{s.name} · {s.domain}</li>)}
        </Section>
        <Section title={`Deployment targets (${data.deploymentTargets.length})`}>
          {data.deploymentTargets.map((t) => <li key={t.target}>{t.target} · {t.serviceCount} services</li>)}
        </Section>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="mb-2 text-sm font-semibold text-slate-700">{title}</h3>
      <ul className="space-y-1 text-sm text-slate-700">{children}</ul>
    </section>
  );
}
```

### `src/presentation/components/GovernancePanel.tsx`
```tsx
import type { GovernanceProjection } from '@esap/observation-client';

const VERDICT_COLORS: Record<string, string> = {
  approve: 'bg-emerald-100 text-emerald-700',
  reject: 'bg-rose-100 text-rose-700',
  defer: 'bg-amber-100 text-amber-700',
  escalate: 'bg-purple-100 text-purple-700',
};

export function GovernancePanel({ data }: { data: GovernanceProjection }) {
  return (
    <div className="space-y-4">
      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h3 className="mb-2 text-sm font-semibold text-slate-700">Council ({data.council.members.length})</h3>
        <ul className="space-y-1 text-sm">
          {data.council.members.map((m) => (
            <li key={m.memberId} className="flex justify-between">
              <span>{m.role} <span className="text-xs text-slate-400">({m.kind})</span></span>
              <span className="font-mono text-xs">w={m.votingWeight}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h3 className="mb-2 text-sm font-semibold text-slate-700">Decisions ({data.decisions.length})</h3>
        <ul className="space-y-2">
          {data.decisions.map((d) => (
            <li key={d.decisionId} className="rounded border border-slate-100 p-3 text-sm">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs text-slate-500">{d.candidateId} · gen {d.generation}</span>
                <span className={`rounded-full px-2 py-0.5 text-xs ${VERDICT_COLORS[d.verdict] ?? 'bg-slate-100 text-slate-600'}`}>{d.verdict}</span>
              </div>
              {d.authorizesTransition && (
                <div className="mt-1 text-xs text-slate-500">{d.authorizesTransition.fromState} → {d.authorizesTransition.toState}</div>
              )}
              <p className="mt-1 text-slate-700">{d.rationale}</p>
              {d.evidenceRefs.length > 0 && (
                <div className="mt-1 text-xs text-slate-400">evidence: {d.evidenceRefs.join(', ')}</div>
              )}
            </li>
          ))}
        </ul>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h3 className="mb-2 text-sm font-semibold text-slate-700">Gates ({data.gates.length})</h3>
        <ul className="space-y-1 text-sm">
          {data.gates.map((g) => (
            <li key={g.gateId}>{g.name} · guards {g.guardsTransitionFrom} → {g.guardsTransitionTo}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}
```

### `src/presentation/components/LineageExplorer.tsx`
```tsx
import { useCandidateLineage } from '@/presentation/hooks/useLineage';

export function LineageExplorer({ candidateId }: { candidateId: string }) {
  const { data, isLoading, error } = useCandidateLineage(candidateId);
  if (isLoading) return <p className="text-sm text-slate-500">Loading lineage…</p>;
  if (error || !data) return <p className="text-sm text-rose-600">Lineage unavailable.</p>;

  return (
    <div className="space-y-4">
      <header>
        <h2 className="text-lg font-semibold">Why does this software exist?</h2>
        <p className="text-sm text-slate-500">
          <span className="font-mono">{data.candidateId}</span> · gen {data.generation} ·{' '}
          ISR <span className="font-mono">{data.isrRevision}</span> · {data.lifecycleState}
        </p>
      </header>

      <LineageSection title="Requirements" items={data.requirements} render={(r) => `${r.requirementId} — ${r.title}`} />
      <LineageSection title="Parents" items={data.parents} render={(p) => `${p.candidateId} (gen ${p.generation})`} />
      <LineageSection title="Evolution operations" items={data.evolutionOperations}
        render={(o) => `${o.operationType}${o.chromosomeFamily ? ` · ${o.chromosomeFamily}` : ''} — ${o.summary}`} />
      <LineageSection title="Fitness evaluations" items={data.fitnessEvaluations}
        render={(e) => `score ${e.aggregateScore ?? '—'}${e.onParetoFrontier ? ' · Pareto frontier' : ''}`} />
      <LineageSection title="Verifications" items={data.verifications} render={(v) => `${v.verificationType}: ${v.result}`} />
      {data.governanceDecision && (
        <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm">
          <h3 className="font-semibold text-slate-700">Governance decision</h3>
          <p className="font-mono text-xs text-slate-500">{data.governanceDecision.decisionId}</p>
          <p>verdict: {data.governanceDecision.verdict}</p>
        </div>
      )}
      <LineageSection title="Deployments" items={data.deployments} render={(d) => `${d.target}: ${d.status}`} />
      <LineageSection title="Operational feedback" items={data.operationalFeedback}
        render={(f) => `${f.signalType}: ${f.summary}${f.influencedNextGeneration ? ' → next gen' : ''}`} />
    </div>
  );
}

function LineageSection<T>({ title, items, render }: { title: string; items: readonly T[]; render: (item: T) => string }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="mb-2 text-sm font-semibold text-slate-700">{title} ({items.length})</h3>
      {items.length === 0 ? (
        <p className="text-xs text-slate-400">None recorded.</p>
      ) : (
        <ul className="space-y-1 text-sm text-slate-700">{items.map((item, i) => <li key={i}>{render(item)}</li>)}</ul>
      )}
    </section>
  );
}
```

---

## Presentation — pages

```tsx
// pages/DashboardPage.tsx
import { EvolutionOverview } from '@/presentation/components/EvolutionOverview';
import { FacetsPanel } from '@/presentation/components/FacetsPanel';

export function DashboardPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Overview</h1>
      <EvolutionOverview />
      <FacetsPanel />
    </div>
  );
}
```
```tsx
// pages/IsrPage.tsx
import { IsrPanel } from '@/presentation/components/IsrPanel';

export function IsrPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">What does the system believe the architecture is?</h1>
      <IsrPanel />
    </div>
  );
}
```
```tsx
// pages/EvolutionPage.tsx
import { EvolutionOverview } from '@/presentation/components/EvolutionOverview';
import { FacetsPanel } from '@/presentation/components/FacetsPanel';

export function EvolutionPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">What is the evolution engine doing?</h1>
      <EvolutionOverview />
      <FacetsPanel />
    </div>
  );
}
```
```tsx
// pages/FitnessPage.tsx
import { FitnessPareto } from '@/presentation/components/FitnessPareto';
import { useFitnessReport } from '@/presentation/hooks/useFitness';
import { useProjection } from '@/presentation/hooks/useProjection';

export function FitnessPage() {
  const { state } = useProjection();
  const generation = state.meta.generation;
  const { data, isLoading, error } = useFitnessReport(generation);
  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Fitness & Pareto</h1>
      {isLoading && <p className="text-sm text-slate-500">Loading fitness report…</p>}
      {(error || !data) && <p className="text-sm text-rose-600">Fitness report unavailable.</p>}
      {data && <FitnessPareto report={data} />}
    </div>
  );
}
```
```tsx
// pages/GovernancePage.tsx
import { GovernancePanel } from '@/presentation/components/GovernancePanel';
import { useGenerationGovernance } from '@/presentation/hooks/useGovernance';
import { useProjection } from '@/presentation/hooks/useProjection';

export function GovernancePage() {
  const { state } = useProjection();
  const generation = state.meta.generation;
  const { data, isLoading, error } = useGenerationGovernance(generation);
  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Why was this allowed to progress?</h1>
      {isLoading && <p className="text-sm text-slate-500">Loading governance…</p>}
      {(error || !data) && <p className="text-sm text-rose-600">Governance unavailable.</p>}
      {data && <GovernancePanel data={data} />}
    </div>
  );
}
```
```tsx
// pages/LineagePage.tsx
import { Link, useParams } from 'react-router-dom';
import { LineageExplorer } from '@/presentation/components/LineageExplorer';
import { useProjection } from '@/presentation/hooks/useProjection';

export function LineagePage() {
  const { candidateId } = useParams<{ candidateId: string }>();
  const { state } = useProjection();
  const candidates = (state.facets.candidates ?? []) as Array<{ candidateId?: string }>;

  if (candidateId) return <LineageExplorer candidateId={candidateId} />;

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Select a candidate to trace its lineage</h1>
      <ul className="space-y-1">
        {candidates.map((c, i) => c.candidateId ? (
          <li key={c.candidateId}>
            <Link to={`/lineage/${c.candidateId}`} className="font-mono text-sm text-brand-700 hover:underline">{c.candidateId}</Link>
          </li>
        ) : <li key={i} className="text-sm text-slate-400">candidate {i}</li>)}
      </ul>
      {candidates.length === 0 && <p className="text-sm text-slate-400">No candidates in the live stream yet.</p>}
    </div>
  );
}
```

---

## Entry

### `src/main.tsx`
```tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { loadRuntimeConfig } from '@/application/configLoader';
import { initTelemetry } from '@/infrastructure/telemetry/otel';
import { ConfigProvider } from '@/presentation/contexts/ConfigContext';
import App from '@/App';
import '@/index.css';

async function bootstrap(): Promise<void> {
  const config = await loadRuntimeConfig();
  initTelemetry(config);

  const queryClient = new QueryClient({
    defaultOptions: { queries: { staleTime: 10_000, refetchOnWindowFocus: false, retry: 1 } },
  });

  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <QueryClientProvider client={queryClient}>
        <ConfigProvider config={config}>
          <BrowserRouter>
            <App />
          </BrowserRouter>
        </ConfigProvider>
      </QueryClientProvider>
    </React.StrictMode>,
  );
}

void bootstrap();
```

### `src/App.tsx`
```tsx
import { useMemo } from 'react';
import { Route, Routes } from 'react-router-dom';
import { useDashboardConfig } from '@/presentation/contexts/ConfigContext';
import { OtelMetricsSink } from '@/infrastructure/telemetry/OtelMetricsSink';
import { ProjectionProvider } from '@/presentation/components/ProjectionProvider';
import { Layout } from '@/presentation/components/Layout';
import { DashboardPage } from '@/presentation/pages/DashboardPage';
import { IsrPage } from '@/presentation/pages/IsrPage';
import { EvolutionPage } from '@/presentation/pages/EvolutionPage';
import { FitnessPage } from '@/presentation/pages/FitnessPage';
import { GovernancePage } from '@/presentation/pages/GovernancePage';
import { LineagePage } from '@/presentation/pages/LineagePage';

export default function App() {
  const config = useDashboardConfig();
  const metricsSink = useMemo(
    () => (config.enableTelemetry ? new OtelMetricsSink(config.serviceName) : undefined),
    [config],
  );

  return (
    <ProjectionProvider config={config} metricsSink={metricsSink}>
      <Layout>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/isr" element={<IsrPage />} />
          <Route path="/evolution" element={<EvolutionPage />} />
          <Route path="/fitness" element={<FitnessPage />} />
          <Route path="/governance" element={<GovernancePage />} />
          <Route path="/lineage" element={<LineagePage />} />
          <Route path="/lineage/:candidateId" element={<LineagePage />} />
        </Routes>
      </Layout>
    </ProjectionProvider>
  );
}
```

---

## Tests

### `src/tests/setup.ts`
```ts
import '@testing-library/jest-dom/vitest';
```

### `src/tests/configLoader.test.ts`
```ts
import { describe, expect, it } from 'vitest';
import { loadRuntimeConfig } from '@/application/configLoader';

describe('loadRuntimeConfig', () => {
  it('merges remote config over defaults', async () => {
    const fetchImpl = (async () => ({
      ok: true, json: async () => ({ streamId: 'custom', enableTelemetry: true }),
    })) as unknown as typeof fetch;
    const config = await loadRuntimeConfig('/config/runtime.json', fetchImpl);
    expect(config.streamId).toBe('custom');
    expect(config.enableTelemetry).toBe(true);
    expect(config.observationApiPath).toBe('/observation');
  });

  it('falls back to defaults on failure', async () => {
    const fetchImpl = (async () => { throw new Error('network'); }) as unknown as typeof fetch;
    const config = await loadRuntimeConfig('/config/runtime.json', fetchImpl);
    expect(config.streamId).toBe('evolution-main');
  });
});
```

### `src/tests/statusStore.test.ts`
```ts
import { describe, expect, it } from 'vitest';
import { getProjectionStatus, resetProjectionStatus, setProjectionStatus, subscribeProjectionStatus } from '@/application/statusStore';

describe('statusStore', () => {
  it('notifies subscribers and stores status', () => {
    resetProjectionStatus();
    let calls = 0;
    const unsub = subscribeProjectionStatus(() => { calls += 1; });
    setProjectionStatus({
      state: 'healthy', streamId: 's', authoritativeSequence: 1, appliedSequence: 1,
      lastSuccessfulSyncAt: null, lastEventAt: null, lastError: null,
    });
    expect(calls).toBe(1);
    expect(getProjectionStatus()?.state).toBe('healthy');
    unsub();
  });
});
```

### `src/tests/ProjectionStatusBanner.test.tsx`
```tsx
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ProjectionStatusBanner } from '@/presentation/components/ProjectionStatusBanner';

vi.mock('@/presentation/hooks/useProjection', () => ({
  useProjection: () => ({
    state: { facets: {}, meta: { generation: 0, facetUpdatedAt: {} } },
    status: {
      state: 'unavailable', streamId: 's', authoritativeSequence: 0, appliedSequence: 0,
      lastSuccessfulSyncAt: null, lastEventAt: null,
      lastError: { code: 'SEC_UNAUTHENTICATED', category: 'security', severity: 'error', message: 'auth', occurredAt: '' },
    },
    metrics: {},
  }),
}));
vi.mock('@/presentation/contexts/ConfigContext', () => ({
  useDashboardConfig: () => ({
    authLoginPath: '/auth/login', observationApiPath: '/observation',
    observationWsPath: '/ws/evolution', streamId: 's', enableTelemetry: false, serviceName: 'd',
  }),
}));

describe('ProjectionStatusBanner', () => {
  it('shows sign-in affordance on SEC_UNAUTHENTICATED', () => {
    render(<ProjectionStatusBanner />);
    expect(screen.getByText('Unavailable')).toBeInTheDocument();
    expect(screen.getByText('Sign in')).toBeInTheDocument();
  });
});
```

---

## Deployment

### `dashboard/nginx.conf`
```nginx
server {
    listen 8080;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    # Same-origin only: /observation, /ws, /config, OTLP/auth all route via ingress.
    add_header Content-Security-Policy "default-src 'self'; img-src 'self' data:; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; font-src 'self';" always;

    location = /healthz {
        access_log off;
        return 200 "ok\n";
        add_header Content-Type text/plain;
    }

    location = /config/runtime.json { add_header Cache-Control "no-store"; }
    location /assets/ { add_header Cache-Control "public, max-age=31536000, immutable"; }
    location / { try_files $uri $uri/ /index.html; }
}
```

### `dashboard/Dockerfile`
```dockerfile
# syntax=docker/dockerfile:1.6
FROM node:20-alpine AS build
WORKDIR /app
COPY observation-client ./observation-client
RUN cd observation-client && npm ci && npm run build
COPY dashboard/package.json ./dashboard/package.json
RUN cd dashboard && npm ci
COPY dashboard/. ./dashboard/
RUN cd dashboard && npm run build

FROM nginx:1.27-alpine AS runtime
COPY --from=build /app/dashboard/dist /usr/share/nginx/html
COPY dashboard/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://localhost:8080/healthz || exit 1
CMD ["nginx", "-g", "daemon off;"]
```

### `dashboard/.dockerignore`
```
node_modules
dist
.git
*.log
coverage
```

### `dashboard/k8s/configmap.yaml`
```yaml
apiVersion: v1
kind: ConfigMap
metadata: { name: esap-dashboard-config, namespace: esap }
data:
  runtime.json: |
    {
      "observationApiPath": "/observation",
      "observationWsPath": "/ws/evolution",
      "streamId": "evolution-main",
      "enableTelemetry": true,
      "otlpTracesEndpoint": "/otlp/v1/traces",
      "otlpMetricsEndpoint": "/otlp/v1/metrics",
      "serviceName": "esap-dashboard",
      "authLoginPath": "/auth/login"
    }
```

### `dashboard/k8s/deployment.yaml`
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: esap-dashboard
  namespace: esap
  labels: { app.kubernetes.io/name: esap-dashboard, app.kubernetes.io/part-of: esap }
spec:
  replicas: 2
  selector: { matchLabels: { app.kubernetes.io/name: esap-dashboard } }
  template:
    metadata:
      labels: { app.kubernetes.io/name: esap-dashboard }
    spec:
      securityContext: { runAsNonRoot: true, seccompProfile: { type: RuntimeDefault } }
      containers:
        - name: dashboard
          image: esap/dashboard:1.1.0
          ports: [{ name: http, containerPort: 8080 }]
          resources:
            requests: { cpu: 50m, memory: 64Mi }
            limits: { cpu: 500m, memory: 256Mi }
          livenessProbe: { httpGet: { path: /healthz, port: http }, initialDelaySeconds: 5, periodSeconds: 10 }
          readinessProbe: { httpGet: { path: /healthz, port: http }, initialDelaySeconds: 3, periodSeconds: 5 }
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities: { drop: ["ALL"] }
          volumeMounts:
            - { name: nginx-cache, mountPath: /var/cache/nginx }
            - { name: nginx-run, mountPath: /var/run }
            - { name: runtime-config, mountPath: /usr/share/nginx/html/config }
      volumes:
        - { name: nginx-cache, emptyDir: {} }
        - { name: nginx-run, emptyDir: {} }
        - name: runtime-config
          configMap: { name: esap-dashboard-config }
```

### `dashboard/k8s/service.yaml`
```yaml
apiVersion: v1
kind: Service
metadata: { name: esap-dashboard, namespace: esap }
spec:
  selector: { app.kubernetes.io/name: esap-dashboard }
  ports: [{ name: http, port: 80, targetPort: http }]
```

### `dashboard/k8s/ingress.yaml`
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: esap
  namespace: esap
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "3600"   # long-lived WS
spec:
  tls: [{ hosts: [esap.example.com], secretName: esap-tls }]
  rules:
    - host: esap.example.com
      http:
        paths:
          - { path: /, pathType: Prefix, backend: { service: { name: esap-dashboard, port: { name: http } } } }
          - { path: /config, pathType: Prefix, backend: { service: { name: esap-dashboard, port: { name: http } } } }
          - { path: /observation, pathType: Prefix, backend: { service: { name: esap-platform-api, port: { name: http } } } }
          - { path: /ws, pathType: Prefix, backend: { service: { name: esap-platform-api, port: { name: http } } } }
          - { path: /auth, pathType: Prefix, backend: { service: { name: esap-auth, port: { name: http } } } }
```

### `dashboard/k8s/hpa.yaml`
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata: { name: esap-dashboard, namespace: esap }
spec:
  scaleTargetRef: { apiVersion: apps/v1, kind: Deployment, name: esap-dashboard }
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource: { name: cpu, target: { type: Utilization, averageUtilization: 60 } }
```

---

## Run & verify

```bash
cd observation-client && npm ci && npm run build   # gate-6-client-build
cd ../dashboard       && npm ci && npm run build   # gate-6-dashboard-build
cd ../dashboard       && npm run typecheck && npm run test   # dashboard-validation
```

This is the complete Phase D: a real, production-ready observation backend that answers all five constitutional questions, is fail-closed, observable, and deployable — and makes `dashboard-build` / `dashboard-validation` measure a genuine artifact rather than an empty tree.