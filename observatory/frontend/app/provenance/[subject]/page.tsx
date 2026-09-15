"use client";

import { useCallback, useEffect, useState } from "react";

import {
  EventTimeline,
  KeyValue,
  Section,
  StatusPill
} from "@/components";
import { api } from "@/lib/api";
import type { ProvenanceAudit } from "@/lib/types";

export default function ProvenanceAuditPage({
  params
}: {
  params: { subject: string };
}) {
  const [audit, setAudit] = useState<ProvenanceAudit | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const nextAudit = await api.provenanceAudit(params.subject);
      setAudit(nextAudit);
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unknown error");
    }
  }, [params.subject]);

  useEffect(() => {
    refresh();

    const interval = setInterval(refresh, 5000);

    return () => {
      clearInterval(interval);
    };
  }, [refresh]);

  if (error && !audit) {
    return <div className="error">Provenance audit unavailable: {error}</div>;
  }

  if (!audit) {
    return <div className="muted">Loading provenance audit…</div>;
  }

  return (
    <div className="grid">
      {error ? <div className="error">{error}</div> : null}

      <Section
        title={`Provenance ${audit.subject_id}`}
        right={<StatusPill status={audit.status} />}
      >
        <KeyValue
          data={{
            entity_type: audit.entity_type,
            direct_events: audit.direct_event_count,
            related_events: audit.related_event_count,
            first_observed_at: new Date(
              audit.first_observed_at
            ).toLocaleString(),
            last_observed_at: new Date(
              audit.last_observed_at
            ).toLocaleString()
          }}
        />
      </Section>

      <div className="grid grid-2">
        <Section title="Categories">
          {audit.categories.length === 0 ? (
            <div className="empty">None</div>
          ) : (
            <ul className="list">
              {audit.categories.map(category => (
                <li key={category}>{category}</li>
              ))}
            </ul>
          )}
        </Section>

        <Section title="Actors / Sources">
          {audit.actors.length === 0 ? (
            <div className="empty">None</div>
          ) : (
            <ul className="list">
              {audit.actors.map(actor => (
                <li key={actor}>{actor}</li>
              ))}
            </ul>
          )}
        </Section>
      </div>

      <Section title="Epistemic State">
        <KeyValue data={audit.epistemic_state} />
      </Section>

      <Section title="Derived Hash Chain">
        {audit.hash_chain.length === 0 ? (
          <div className="empty">
            No direct events available for hash-chain derivation.
          </div>
        ) : (
          <ul className="timeline">
            {audit.hash_chain.map(entry => (
              <li key={entry.event_id} className="timeline-item">
                <div className="timeline-top">
                  <span>{entry.event_id}</span>
                  <span className="timeline-time">
                    {new Date(entry.timestamp).toLocaleString()}
                  </span>
                </div>

                <div className="timeline-meta">
                  <span>hash {entry.event_hash}</span>
                  <span>
                    previous {entry.previous_event_hash ?? "genesis"}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Entities">
        {audit.nodes.length === 0 ? (
          <div className="empty">No entities recorded</div>
        ) : (
          <ul className="timeline">
            {audit.nodes.map(node => (
              <li key={node.id} className="timeline-item">
                <div className="timeline-top">
                  <span>{node.id}</span>
                  <StatusPill status={node.entity_type} />
                </div>

                <div className="timeline-meta">
                  <span>events {node.event_count}</span>
                  <span>
                    last observed{" "}
                    {node.last_observed_at
                      ? new Date(node.last_observed_at).toLocaleString()
                      : "unknown"}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Relations">
        {audit.edges.length === 0 ? (
          <div className="empty">No relations recorded</div>
        ) : (
          <ul className="list">
            {audit.edges.map(edge => (
              <li
                key={`${edge.source}:${edge.target}:${edge.relation}:${edge.event_id}`}
              >
                {edge.source} — {edge.relation} → {edge.target}
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Warnings">
        {audit.warnings.length === 0 ? (
          <div className="empty">None</div>
        ) : (
          <ul className="timeline">
            {audit.warnings.map(warning => (
              <li key={warning.warning_id} className="timeline-item">
                <div className="timeline-top">
                  <span>{warning.type}</span>
                  <StatusPill status={warning.severity} />
                </div>

                <div className="timeline-summary">{warning.summary}</div>

                <div className="timeline-meta">
                  <span>event {warning.event_type}</span>
                  <span>subject {warning.subject_id}</span>
                  <span>
                    {new Date(warning.timestamp).toLocaleString()}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Governance Events">
        {audit.governance_events.length === 0 ? (
          <div className="empty">None</div>
        ) : (
          <EventTimeline items={audit.governance_events} />
        )}
      </Section>

      <Section title="Full Timeline">
        <EventTimeline items={audit.timeline} />
      </Section>
    </div>
  );
}
