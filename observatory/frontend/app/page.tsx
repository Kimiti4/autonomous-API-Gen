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
