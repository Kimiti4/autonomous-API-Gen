"use client";

import { useCallback, useEffect, useState } from "react";

import {
  EpistemicBadge,
  KeyValue,
  Section
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
