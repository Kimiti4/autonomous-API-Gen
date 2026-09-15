Yes — proceeding.

The next production layer is the **Observatory frontend foundation**.

This foundation must obey the constitutional rule:

> The frontend is a presentation boundary.  
> It must not contain governance logic, epistemic classification logic, authorization logic, or privileged secrets.

The frontend renders the authoritative backend read models:

```text
Python Observatory backend
        ↓
HTTP / SSE read models
        ↓
TypeScript / React frontend
        ↓
Human operational picture
```

---

# 1. Frontend structure

Create:

```text
observatory/
└── frontend/
    ├── package.json
    ├── tsconfig.json
    ├── next.config.mjs
    ├── .env.example
    ├── app/
    │   ├── layout.tsx
    │   ├── globals.css
    │   ├── page.tsx
    │   ├── runtime/
    │   │   └── page.tsx
    │   ├── governance/
    │   │   └── page.tsx
    │   ├── evolution/
    │   │   └── [id]/
    │   │       └── page.tsx
    │   └── evidence/
    │       └── [id]/
    │           └── page.tsx
    ├── components/
    │   ├── index.ts
    │   ├── Section.tsx
    │   ├── StatusPill.tsx
    │   ├── EpistemicBadge.tsx
    │   ├── KeyValue.tsx
    │   └── EventTimeline.tsx
    └── lib/
        ├── types.ts
        ├── api.ts
        └── use-event-stream.ts
```

---

# 2. Package definition

**`observatory/frontend/package.json`**

```json
{
  "name": "tiannara-observatory-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  },
  "dependencies": {
    "next": "14.2.3",
    "react": "18.3.1",
    "react-dom": "18.3.1"
  },
  "devDependencies": {
    "@types/node": "20.12.12",
    "@types/react": "18.3.3",
    "@types/react-dom": "18.3.0",
    "typescript": "5.4.5"
  }
}
```

---

# 3. TypeScript configuration

**`observatory/frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [
      {
        "name": "next"
      }
    ],
    "paths": {
      "@/*": ["./*"]
    }
  },
  "include": [
    "next-env.d.ts",
    "**/*.ts",
    "**/*.tsx",
    ".next/types/**/*.ts"
  ],
  "exclude": [
    "node_modules"
  ]
}
```

---

# 4. Next configuration

**`observatory/frontend/next.config.mjs`**

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true
};

export default nextConfig;
```

---

# 5. Environment template

**`observatory/frontend/.env.example`**

```bash
NEXT_PUBLIC_OBSERVATORY_API_URL=http://127.0.0.1:8000
```

Important security rule:

```text
Do NOT place OBSERVATORY_API_TOKEN in a NEXT_PUBLIC variable.
Browser-facing code must not hold privileged Observatory tokens.
```

If the backend requires a token, put an authenticated gateway or reverse proxy in front of the backend.

---

# 6. Frontend type model

**`observatory/frontend/lib/types.ts`**

```typescript
export type EpistemicStatus =
  | "observed"
  | "inferred"
  | "unknown"
  | "contradiction";

export type Severity =
  | "debug"
  | "info"
  | "warning"
  | "error"
  | "fatal";

export type EventCategory =
  | "runtime"
  | "evidence"
  | "evolution"
  | "governance"
  | "knowledge";

export interface ObservatoryEvent {
  id: string;
  timestamp: string;
  source: string;
  category: EventCategory;
  type: string;
  subject_id: string;
  correlation_id?: string | null;
  causation_id?: string | null;
  payload: Record<string, unknown>;
  epistemic_status: EpistemicStatus;
  authorization?: string | null;
  evidence_refs: string[];
  provenance: Record<string, unknown>;
  severity: Severity;
}

export interface TimelineEntry {
  event_id: string;
  timestamp: string;
  category: EventCategory;
  type: string;
  subject_id: string;
  epistemic_status: EpistemicStatus;
  severity: Severity;
  summary: string;
}

export interface CurrentCycle {
  evolution_id: string;
  latest_event_type: string;
  updated_at: string;
}

export interface RuntimeState {
  processes: number;
  supervisors: number;
  messages_per_sec: number | string;
  memory_total: number | string;
  restart_count: number;
  health: string;
  updated_at: string | null;
}

export interface AuthorityState {
  interpretation: string;
  evolution: string;
  implementation: string;
  runtime: string;
  deployment: string;
  production: string;
  governance: string;
}

export interface GateState {
  gate: string;
  status: string;
}

export interface CommandActivity {
  requested: number;
  accepted: number;
  rejected: number;
}

export interface GovernanceState {
  current_authority: AuthorityState;
  active_gates: GateState[];
  safe_mode: string;
  human_controls: string[];
  command_activity: CommandActivity;
}

export interface OverviewState {
  current_cycle: CurrentCycle | null;
  status: string;
  runtime_health: string;
  safe_mode: string;
  evidence_count: number;
  authorization_state: string;
  recent_event_count: number;
}

export interface PipelineStage {
  stage: string;
  status: string;
}

export interface EpistemicCounts {
  observed: number;
  inferred: number;
  unknown: number;
  contradiction: number;
}

export interface EvolutionState {
  evolution_id: string;
  status: string;
  epistemic_state: EpistemicCounts;
  capability_check: Record<string, string>;
  pipeline: PipelineStage[];
  decision: string;
  authorization: AuthorityState;
  unknowns: string[];
  contradictions: string[];
  updated_at: string | null;
}

export interface EvidenceRecord {
  evidence_id: string;
  epistemic_status: EpistemicStatus;
  claim: string;
  result: string;
  scope: string[];
  not_proven: string[];
  provenance: Record<string, unknown>;
  observed_at: string | null;
}

export interface DashboardState {
  overview: OverviewState;
  runtime: RuntimeState;
  governance: GovernanceState;
  timeline: TimelineEntry[];
}
```

---

# 7. API client

**`observatory/frontend/lib/api.ts`**

```typescript
import type {
  DashboardState,
  EvidenceRecord,
  EvolutionState,
  GovernanceState,
  OverviewState,
  RuntimeState,
  TimelineEntry
} from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_OBSERVATORY_API_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    cache: "no-store",
    ...init
  });

  if (!response.ok) {
    let detail: unknown = response.statusText;

    try {
      const body = await response.json();
      detail = body.detail ?? body.error ?? body;
    } catch {
      // Keep the HTTP status text when the body is not JSON.
    }

    const message =
      typeof detail === "string" ? detail : JSON.stringify(detail);

    throw new ApiError(response.status, message);
  }

  return (await response.json()) as T;
}

export const api = {
  dashboard(): Promise<DashboardState> {
    return request<DashboardState>("/observatory/dashboard");
  },

  overview(): Promise<OverviewState> {
    return request<OverviewState>("/observatory/overview");
  },

  runtime(): Promise<RuntimeState> {
    return request<RuntimeState>("/observatory/runtime");
  },

  governance(): Promise<GovernanceState> {
    return request<GovernanceState>("/observatory/governance");
  },

  timeline(subject?: string, limit = 50): Promise<TimelineEntry[]> {
    const params = new URLSearchParams();

    if (subject) {
      params.set("subject", subject);
    }

    params.set("limit", String(limit));

    return request<TimelineEntry[]>(
      `/observatory/timeline?${params.toString()}`
    );
  },

  evolution(evolutionId: string): Promise<EvolutionState> {
    return request<EvolutionState>(
      `/observatory/evolution/${encodeURIComponent(evolutionId)}`
    );
  },

  evidence(evidenceId: string): Promise<EvidenceRecord> {
    return request<EvidenceRecord>(
      `/observatory/evidence/${encodeURIComponent(evidenceId)}`
    );
  }
};
```

---

# 8. Live event stream hook

**`observatory/frontend/lib/use-event-stream.ts`**

```typescript
"use client";

import { useEffect, useState } from "react";

import type { ObservatoryEvent, TimelineEntry } from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_OBSERVATORY_API_URL ?? "http://127.0.0.1:8000";

function eventToTimelineEntry(event: ObservatoryEvent): TimelineEntry {
  const summary =
    typeof event.payload?.summary === "string"
      ? event.payload.summary
      : `${event.type}: ${event.subject_id}`;

  return {
    event_id: event.id,
    timestamp: event.timestamp,
    category: event.category,
    type: event.type,
    subject_id: event.subject_id,
    epistemic_status: event.epistemic_status,
    severity: event.severity,
    summary
  };
}

export function useEventTimeline(limit = 100) {
  const [items, setItems] = useState<TimelineEntry[]>([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const source = new EventSource(`${API_BASE}/observatory/stream`);

    source.onopen = () => {
      setConnected(true);
    };

    source.onerror = () => {
      setConnected(false);
    };

    source.onmessage = message => {
      try {
        const event = JSON.parse(message.data) as ObservatoryEvent;
        const entry = eventToTimelineEntry(event);

        setItems(previous => [entry, ...previous].slice(0, limit));
      } catch {
        // Ignore malformed stream payloads.
      }
    };

    return () => {
      source.close();
    };
  }, [limit]);

  return {
    items,
    connected
  };
}
```

---

# 9. Shared components

**`observatory/frontend/components/index.ts`**

```typescript
export { Section } from "./Section";
export { StatusPill } from "./StatusPill";
export { EpistemicBadge } from "./EpistemicBadge";
export { KeyValue } from "./KeyValue";
export { EventTimeline } from "./EventTimeline";
```

---

**`observatory/frontend/components/Section.tsx`**

```typescript
import type { ReactNode } from "react";

export function Section({
  title,
  right,
  children
}: {
  title: string;
  right?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="section">
      <div className="section-header">
        <h2>{title}</h2>
        {right ? <div className="section-right">{right}</div> : null}
      </div>

      <div className="section-body">{children}</div>
    </section>
  );
}
```

---

**`observatory/frontend/components/StatusPill.tsx`**

```typescript
export function StatusPill({ status }: { status: string }) {
  const normalized = String(status || "unknown")
    .toLowerCase()
    .replaceAll(" ", "-");

  return <span className={`pill pill-${normalized}`}>{normalized}</span>;
}
```

---

**`observatory/frontend/components/EpistemicBadge.tsx`**

```typescript
import type { EpistemicStatus } from "@/lib/types";

export function EpistemicBadge({ status }: { status: EpistemicStatus }) {
  const normalized = String(status || "unknown").toLowerCase();

  return (
    <span className={`epistemic epistemic-${normalized}`}>{normalized}</span>
  );
}
```

---

**`observatory/frontend/components/KeyValue.tsx`**

```typescript
function formatValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "unknown";
  }

  if (typeof value === "object") {
    return JSON.stringify(value);
  }

  return String(value);
}

export function KeyValue({ data }: { data: Record<string, unknown> }) {
  const entries = Object.entries(data || {});

  if (entries.length === 0) {
    return <div className="empty">None</div>;
  }

  return (
    <dl className="key-value">
      {entries.map(([key, value]) => (
        <div key={key} className="key-value-row">
          <dt>{key}</dt>
          <dd>{formatValue(value)}</dd>
        </div>
      ))}
    </dl>
  );
}
```

---

**`observatory/frontend/components/EventTimeline.tsx`**

```typescript
import type { TimelineEntry } from "@/lib/types";

import { EpistemicBadge } from "./EpistemicBadge";

function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);

  if (Number.isNaN(date.getTime())) {
    return timestamp;
  }

  return date.toLocaleString();
}

export function EventTimeline({ items }: { items: TimelineEntry[] }) {
  if (items.length === 0) {
    return <div className="empty">No events</div>;
  }

  return (
    <ul className="timeline">
      {items.map(item => (
        <li key={item.event_id} className="timeline-item">
          <div className="timeline-top">
            <span className="timeline-time">
              {formatTimestamp(item.timestamp)}
            </span>

            <EpistemicBadge status={item.epistemic_status} />
          </div>

          <div className="timeline-summary">{item.summary}</div>

          <div className="timeline-meta">
            <span>{item.category}</span>
            <span>{item.type}</span>
            <span>{item.subject_id}</span>
            <span>{item.severity}</span>
          </div>
        </li>
      ))}
    </ul>
  );
}
```

---

# 10. Root layout

**`observatory/frontend/app/layout.tsx`**

```typescript
import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: "Tiannara Observatory",
  description:
    "Observatory console for Tiannara runtime, evidence, evolution, and governance state."
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="app-header">
          <div className="app-title">
            <h1>Tiannara Observatory</h1>
            <p>Runtime, evidence, evolution, and governance state</p>
          </div>

          <nav className="app-nav">
            <a href="/">Overview</a>
            <a href="/runtime">Runtime</a>
            <a href="/governance">Governance</a>
          </nav>
        </header>

        <main className="app-main">{children}</main>
      </body>
    </html>
  );
}
```

---

# 11. Global stylesheet

**`observatory/frontend/app/globals.css`**

```css
:root {
  color-scheme: dark;
  --background: #05070c;
  --panel: #0b1018;
  --panel-border: #1d2736;
  --text: #d8e0ea;
  --muted: #7d8b9d;
  --accent: #6ea8fe;
  --green: #2fbf71;
  --yellow: #e5b93d;
  --red: #e05252;
  --blue: #5aa9ff;
  --purple: #b48cff;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  background: var(--background);
  color: var(--text);
  font-family: "Inter", "Segoe UI", sans-serif;
}

a {
  color: var(--accent);
  text-decoration: none;
}

a:hover {
  text-decoration: underline;
}

.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 24px;
  border-bottom: 1px solid var(--panel-border);
  background: rgba(5, 7, 12, 0.95);
  position: sticky;
  top: 0;
  z-index: 10;
}

.app-title h1 {
  margin: 0;
  font-size: 20px;
}

.app-title p {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 13px;
}

.app-nav {
  display: flex;
  gap: 18px;
  font-size: 14px;
}

.app-main {
  padding: 24px;
  display: grid;
  gap: 18px;
}

.section {
  background: var(--panel);
  border: 1px solid var(--panel-border);
  border-radius: 10px;
  overflow: hidden;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  border-bottom: 1px solid var(--panel-border);
}

.section-header h2 {
  margin: 0;
  font-size: 15px;
}

.section-body {
  padding: 16px;
}

.grid {
  display: grid;
  gap: 18px;
}

.grid-2 {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.grid-3 {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

@media (max-width: 1000px) {
  .grid-2,
  .grid-3 {
    grid-template-columns: 1fr;
  }
}

.pill,
.epistemic {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 3px 9px;
  font-size: 11px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  border: 1px solid transparent;
}

.pill-operational,
.pill-green,
.pill-pass,
.pill-done {
  color: var(--green);
  border-color: rgba(47, 191, 113, 0.35);
  background: rgba(47, 191, 113, 0.08);
}

.pill-degraded,
.pill-warning,
.pill-current {
  color: var(--yellow);
  border-color: rgba(229, 185, 61, 0.35);
  background: rgba(229, 185, 61, 0.08);
}

.pill-safe-mode,
.pill-safe_mode {
  color: var(--blue);
  border-color: rgba(90, 169, 255, 0.35);
  background: rgba(90, 169, 255, 0.08);
}

.pill-unknown,
.pill-pending {
  color: var(--muted);
  border-color: rgba(125, 139, 157, 0.35);
  background: rgba(125, 139, 157, 0.08);
}

.pill-blocked,
.pill-failed,
.pill-error,
.pill-fatal {
  color: var(--red);
  border-color: rgba(224, 82, 82, 0.35);
  background: rgba(224, 82, 82, 0.08);
}

.pill-in-progress {
  color: var(--blue);
  border-color: rgba(90, 169, 255, 0.35);
  background: rgba(90, 169, 255, 0.08);
}

.epistemic-observed {
  color: var(--green);
  border-color: rgba(47, 191, 113, 0.35);
  background: rgba(47, 191, 113, 0.08);
}

.epistemic-inferred {
  color: var(--blue);
  border-color: rgba(90, 169, 255, 0.35);
  background: rgba(90, 169, 255, 0.08);
}

.epistemic-unknown {
  color: var(--muted);
  border-color: rgba(125, 139, 157, 0.35);
  background: rgba(125, 139, 157, 0.08);
}

.epistemic-contradiction {
  color: var(--red);
  border-color: rgba(224, 82, 82, 0.35);
  background: rgba(224, 82, 82, 0.08);
}

.key-value {
  margin: 0;
  display: grid;
  gap: 8px;
}

.key-value-row {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 12px;
  align-items: baseline;
}

.key-value dt {
  color: var(--muted);
  font-size: 13px;
}

.key-value dd {
  margin: 0;
  font-family: "JetBrains Mono", monospace;
  font-size: 13px;
  overflow-wrap: anywhere;
}

.timeline {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 10px;
}

.timeline-item {
  border: 1px solid var(--panel-border);
  border-radius: 8px;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.015);
}

.timeline-top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.timeline-time {
  color: var(--muted);
  font-size: 12px;
}

.timeline-summary {
  margin-top: 6px;
  font-size: 14px;
}

.timeline-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
  color: var(--muted);
  font-size: 12px;
}

.timeline-meta span {
  border: 1px solid var(--panel-border);
  border-radius: 4px;
  padding: 2px 6px;
}

.empty {
  color: var(--muted);
  font-size: 14px;
}

.error {
  color: var(--red);
  border: 1px solid rgba(224, 82, 82, 0.35);
  background: rgba(224, 82, 82, 0.08);
  padding: 14px 16px;
  border-radius: 8px;
}

.notice {
  color: var(--muted);
  border: 1px solid var(--panel-border);
  background: rgba(255, 255, 255, 0.02);
  padding: 12px 14px;
  border-radius: 8px;
  font-size: 14px;
}

.pipeline {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 8px;
}

.pipeline-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  border: 1px solid var(--panel-border);
  border-radius: 8px;
  padding: 10px 12px;
}

.list {
  margin: 0;
  padding-left: 18px;
  display: grid;
  gap: 6px;
}

.muted {
  color: var(--muted);
}
```

---

# 12. Overview page

**`observatory/frontend/app/page.tsx`**

```typescript
"use client";

import { useCallback, useEffect, useState } from "react";

import {
  EventTimeline,
  KeyValue,
  Section,
  StatusPill
} from "@/components";
import { api } from "@/lib/api";
import { useEventTimeline } from "@/lib/use-event-stream";
import type { DashboardState } from "@/lib/types";

export default function OverviewPage() {
  const [dashboard, setDashboard] = useState<DashboardState | null>(null);
  const [error, setError] = useState<string | null>(null);

  const stream = useEventTimeline(50);

  const refresh = useCallback(async () => {
    try {
      const nextDashboard = await api.dashboard();
      setDashboard(nextDashboard);
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unknown error");
    }
  }, []);

  useEffect(() => {
    refresh();

    const interval = setInterval(refresh, 5000);

    return () => {
      clearInterval(interval);
    };
  }, [refresh]);

  if (error && !dashboard) {
    return <div className="error">Observatory unavailable: {error}</div>;
  }

  if (!dashboard) {
    return <div className="muted">Loading Observatory state…</div>;
  }

  const timeline = stream.items.length > 0 ? stream.items : dashboard.timeline;

  return (
    <div className="grid">
      {error ? <div className="error">{error}</div> : null}

      <div className="grid grid-3">
        <Section title="Current Cycle">
          {dashboard.overview.current_cycle ? (
            <KeyValue
              data={{
                evolution_id: dashboard.overview.current_cycle.evolution_id,
                latest_event_type:
                  dashboard.overview.current_cycle.latest_event_type,
                updated_at: dashboard.overview.current_cycle.updated_at
              }}
            />
          ) : (
            <div className="empty">No active evolution cycle</div>
          )}
        </Section>

        <Section
          title="System Status"
          right={<StatusPill status={dashboard.overview.status} />}
        >
          <KeyValue
            data={{
              runtime_health: dashboard.overview.runtime_health,
              safe_mode: dashboard.overview.safe_mode,
              evidence_count: dashboard.overview.evidence_count,
              authorization_state: dashboard.overview.authorization_state,
              recent_event_count: dashboard.overview.recent_event_count
            }}
          />
        </Section>

        <Section title="Stream">
          <KeyValue
            data={{
              connected: stream.connected ? "yes" : "no",
              stream_items: stream.items.length
            }}
          />
        </Section>
      </div>

      <div className="grid grid-2">
        <Section title="Runtime">
          <KeyValue
            data={{
              processes: dashboard.runtime.processes,
              supervisors: dashboard.runtime.supervisors,
              messages_per_sec: dashboard.runtime.messages_per_sec,
              memory_total: dashboard.runtime.memory_total,
              restart_count: dashboard.runtime.restart_count,
              health: dashboard.runtime.health,
              updated_at: dashboard.runtime.updated_at ?? "unknown"
            }}
          />
        </Section>

        <Section title="Governance">
          <KeyValue data={dashboard.governance.current_authority} />
        </Section>
      </div>

      <Section
        title="Live Event Stream"
        right={<StatusPill status={stream.connected ? "connected" : "disconnected"} />}
      >
        <EventTimeline items={timeline} />
      </Section>
    </div>
  );
}
```

---

# 13. Runtime page

**`observatory/frontend/app/runtime/page.tsx`**

```typescript
"use client";

import { useCallback, useEffect, useState } from "react";

import { KeyValue, Section, StatusPill } from "@/components";
import { api } from "@/lib/api";
import type { RuntimeState } from "@/lib/types";

export default function RuntimePage() {
  const [runtime, setRuntime] = useState<RuntimeState | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const nextRuntime = await api.runtime();
      setRuntime(nextRuntime);
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unknown error");
    }
  }, []);

  useEffect(() => {
    refresh();

    const interval = setInterval(refresh, 5000);

    return () => {
      clearInterval(interval);
    };
  }, [refresh]);

  if (error && !runtime) {
    return <div className="error">Runtime state unavailable: {error}</div>;
  }

  if (!runtime) {
    return <div className="muted">Loading runtime state…</div>;
  }

  return (
    <div className="grid">
      {error ? <div className="error">{error}</div> : null}

      <Section title="Runtime" right={<StatusPill status={runtime.health} />}>
        <KeyValue
          data={{
            processes: runtime.processes,
            supervisors: runtime.supervisors,
            messages_per_sec: runtime.messages_per_sec,
            memory_total: runtime.memory_total,
            restart_count: runtime.restart_count,
            health: runtime.health,
            updated_at: runtime.updated_at ?? "unknown"
          }}
        />
      </Section>
    </div>
  );
}
```

---

# 14. Governance page

**`observatory/frontend/app/governance/page.tsx`**

```typescript
"use client";

import { useCallback, useEffect, useState } from "react";

import { KeyValue, Section, StatusPill } from "@/components";
import { api } from "@/lib/api";
import type { GovernanceState } from "@/lib/types";

export default function GovernancePage() {
  const [governance, setGovernance] = useState<GovernanceState | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const nextGovernance = await api.governance();
      setGovernance(nextGovernance);
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unknown error");
    }
  }, []);

  useEffect(() => {
    refresh();

    const interval = setInterval(refresh, 5000);

    return () => {
      clearInterval(interval);
    };
  }, [refresh]);

  if (error && !governance) {
    return <div className="error">Governance state unavailable: {error}</div>;
  }

  if (!governance) {
    return <div className="muted">Loading governance state…</div>;
  }

  return (
    <div className="grid">
      {error ? <div className="error">{error}</div> : null}

      <div className="grid grid-2">
        <Section
          title="Current Authority"
          right={<StatusPill status={governance.safe_mode} />}
        >
          <KeyValue data={governance.current_authority} />
        </Section>

        <Section title="Command Activity">
          <KeyValue data={governance.command_activity} />
        </Section>
      </div>

      <Section title="Active Gates">
        {governance.active_gates.length === 0 ? (
          <div className="empty">No active gates</div>
        ) : (
          <ul className="pipeline">
            {governance.active_gates.map(gate => (
              <li key={gate.gate} className="pipeline-item">
                <span>{gate.gate}</span>
                <StatusPill status={gate.status} />
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Human Controls">
        <div className="notice">
          Command submission requires an authorized operator gateway. This
          console is currently read-only and does not bypass governance.
        </div>

        <div style={{ height: 12 }} />

        <KeyValue
          data={Object.fromEntries(
            governance.human_controls.map(control => [control, "not authorized"])
          )}
        />
      </Section>
    </div>
  );
}
```

---

# 15. Evolution detail page

**`observatory/frontend/app/evolution/[id]/page.tsx`**

```typescript
"use client";

import { useCallback, useEffect, useState } from "react";

import {
  EpistemicBadge,
  KeyValue,
  Section,
  StatusPill
} from "@/components";
import { api } from "@/lib/api";
import type { EvolutionState } from "@/lib/types";

export default function EvolutionDetailPage({
  params
}: {
  params: { id: string };
}) {
  const [evolution, setEvolution] = useState<EvolutionState | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const nextEvolution = await api.evolution(params.id);
      setEvolution(nextEvolution);
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unknown error");
    }
  }, [params.id]);

  useEffect(() => {
    refresh();

    const interval = setInterval(refresh, 5000);

    return () => {
      clearInterval(interval);
    };
  }, [refresh]);

  if (error && !evolution) {
    return <div className="error">Evolution unavailable: {error}</div>;
  }

  if (!evolution) {
    return <div className="muted">Loading evolution…</div>;
  }

  return (
    <div className="grid">
      {error ? <div className="error">{error}</div> : null}

      <Section
        title={`Evolution ${evolution.evolution_id}`}
        right={<StatusPill status={evolution.status} />}
      >
        <KeyValue
          data={{
            decision: evolution.decision,
            updated_at: evolution.updated_at ?? "unknown"
          }}
        />
      </Section>

      <div className="grid grid-2">
        <Section title="Epistemic State">
          <KeyValue data={evolution.epistemic_state} />
        </Section>

        <Section title="Capability Check">
          <KeyValue data={evolution.capability_check} />
        </Section>
      </div>

      <Section title="Pipeline">
        <ul className="pipeline">
          {evolution.pipeline.map(stage => (
            <li key={stage.stage} className="pipeline-item">
              <span>{stage.stage}</span>
              <StatusPill status={stage.status} />
            </li>
          ))}
        </ul>
      </Section>

      <Section title="Authorization">
        <KeyValue data={evolution.authorization} />
      </Section>

      <div className="grid grid-2">
        <Section title="Unknowns">
          {evolution.unknowns.length === 0 ? (
            <div className="empty">None</div>
          ) : (
            <ul className="list">
              {evolution.unknowns.map(unknown => (
                <li key={unknown}>{unknown}</li>
              ))}
            </ul>
          )}
        </Section>

        <Section title="Contradictions">
          {evolution.contradictions.length === 0 ? (
            <div className="empty">None</div>
          ) : (
            <ul className="list">
              {evolution.contradictions.map(contradiction => (
                <li key={contradiction}>{contradiction}</li>
              ))}
            </ul>
          )}
        </Section>
      </div>
    </div>
  );
}
```

---

# 16. Evidence detail page

**`observatory/frontend/app/evidence/[id]/page.tsx`**

```typescript
"use client";

import { useCallback, useEffect, useState } from "react";

import {
  EpistemicBadge,
  KeyValue,
  Section,
  StatusPill
} from "@/components";
import { api } from "@/lib/api";
import type { EvidenceRecord } from "@/lib/types";

export default function EvidenceDetailPage({
  params
}: {
  params: { id: string };
}) {
  const [evidence, setEvidence] = useState<EvidenceRecord | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const nextEvidence = await api.evidence(params.id);
      setEvidence(nextEvidence);
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unknown error");
    }
  }, [params.id]);

  useEffect(() => {
    refresh();

    const interval = setInterval(refresh, 5000);

    return () => {
      clearInterval(interval);
    };
  }, [refresh]);

  if (error && !evidence) {
    return <div className="error">Evidence unavailable: {error}</div>;
  }

  if (!evidence) {
    return <div className="muted">Loading evidence…</div>;
  }

  return (
    <div className="grid">
      {error ? <div className="error">{error}</div> : null}

      <Section
        title={`Evidence ${evidence.evidence_id}`}
        right={<EpistemicBadge status={evidence.epistemic_status} />}
      >
        <KeyValue
          data={{
            claim: evidence.claim,
            result: evidence.result,
            observed_at: evidence.observed_at ?? "unknown"
          }}
        />
      </Section>

      <div className="grid grid-2">
        <Section title="Scope">
          {evidence.scope.length === 0 ? (
            <div className="empty">None</div>
          ) : (
            <ul className="list">
              {evidence.scope.map(item => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          )}
        </Section>

        <Section title="Not Proven">
          {evidence.not_proven.length === 0 ? (
            <div className="empty">None</div>
          ) : (
            <ul className="list">
              {evidence.not_proven.map(item => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          )}
        </Section>
      </div>

      <Section title="Provenance">
        <KeyValue data={evidence.provenance} />
      </Section>
    </div>
  );
}
```

---

# 17. Run the frontend

From the repository root:

```bash
cd observatory/frontend
npm install
npm run dev
```

The frontend will be available at:

```text
http://127.0.0.1:3000
```

The backend should already be running at:

```text
http://127.0.0.1:8000
```

If needed, override the backend URL:

```bash
cp .env.example .env.local
```

Then edit:

```bash
NEXT_PUBLIC_OBSERVATORY_API_URL=http://127.0.0.1:8000
```

---

# 18. What this frontend foundation establishes

This gives Tiannara a real human console that:

```text
shows current operational status
shows runtime health
shows governance authority
shows live event stream
shows evolution cycles
shows evidence records
preserves epistemic distinctions
does not fabricate data
does not contain governance logic
does not hold privileged tokens
```

It is intentionally a **read-first Observatory console**.

Command issuance should be added only after an authenticated operator boundary is introduced.

---

# 19. Next recommended step

The next frontend/backend integration step is:

```text
Authenticated command proxy
```

That layer should provide:

```text
operator authentication
command authorization
audit attribution
safe-mode controls
bounded command submission
```

It must not place privileged tokens in the browser.

After that, the next UI surfaces are:

```text
Requirements / ISR view
Knowledge view
Experiments view
Capability explorer
Trace explorer
```