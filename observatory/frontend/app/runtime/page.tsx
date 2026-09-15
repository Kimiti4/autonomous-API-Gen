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
