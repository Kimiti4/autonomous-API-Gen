"use client";

import { useCallback, useEffect, useState } from "react";

import { CommandPanel, KeyValue, Section, StatusPill } from "@/components";
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
        <CommandPanel />
      </Section>
    </div>
  );
}
