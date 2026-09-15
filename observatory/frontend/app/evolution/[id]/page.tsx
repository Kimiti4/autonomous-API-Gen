"use client";

import { useCallback, useEffect, useState } from "react";

import {
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
