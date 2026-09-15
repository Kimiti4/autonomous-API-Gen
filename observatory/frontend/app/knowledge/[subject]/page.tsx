"use client";

import { useCallback, useEffect, useState } from "react";

import {
  EpistemicBadge,
  EventTimeline,
  KeyValue,
  Section,
  StatusPill
} from "@/components";
import { api } from "@/lib/api";
import type { KnowledgeMemory } from "@/lib/types";

export default function KnowledgeMemoryPage({
  params
}: {
  params: { subject: string };
}) {
  const [memory, setMemory] = useState<KnowledgeMemory | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const nextMemory = await api.knowledgeMemory(params.subject);
      setMemory(nextMemory);
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

  if (error && !memory) {
    return <div className="error">Knowledge memory unavailable: {error}</div>;
  }

  if (!memory) {
    return <div className="muted">Loading knowledge memory…</div>;
  }

  return (
    <div className="grid">
      {error ? <div className="error">{error}</div> : null}

      <Section
        title={`Knowledge ${memory.subject_id}`}
        right={<StatusPill status={memory.status} />}
      >
        <KeyValue
          data={{
            updated_at: memory.updated_at ?? "unknown",
            first_observed_at: memory.first_observed_at ?? "unknown",
            sources: memory.sources.join(", "),
            evidence_count: memory.evidence_refs.length,
            decision_count: memory.decisions.length,
            memory_record_count: memory.memories.length
          }}
        />
      </Section>

      <div className="grid grid-2">
        <Section title="Epistemic State">
          <KeyValue data={memory.epistemic_state} />
        </Section>

        <Section title="Provenance">
          <KeyValue data={memory.provenance} />
        </Section>
      </div>

      <Section title="Facts">
        {memory.facts.length === 0 ? (
          <div className="empty">No recorded facts</div>
        ) : (
          <ul className="timeline">
            {memory.facts.map(fact => (
              <li key={fact.fact_id} className="timeline-item">
                <div className="timeline-top">
                  <EpistemicBadge status={fact.epistemic_status} />
                  <span className="timeline-time">
                    {new Date(fact.timestamp).toLocaleString()}
                  </span>
                </div>

                <div className="timeline-summary">{fact.statement}</div>

                <div className="timeline-meta">
                  <span>source {fact.source}</span>
                  <span>severity {fact.severity}</span>
                  <span>evidence {fact.evidence_refs.length}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <div className="grid grid-2">
        <Section title="Unknowns">
          {memory.unknowns.length === 0 ? (
            <div className="empty">None</div>
          ) : (
            <ul className="list">
              {memory.unknowns.map(unknown => (
                <li key={unknown.unknown_id}>
                  {unknown.question}
                  <div className="muted">{unknown.reason}</div>
                </li>
              ))}
            </ul>
          )}
        </Section>

        <Section title="Contradictions">
          {memory.contradictions.length === 0 ? (
            <div className="empty">None</div>
          ) : (
            <ul className="list">
              {memory.contradictions.map(contradiction => (
                <li key={contradiction.contradiction_id}>
                  {contradiction.statement}
                  <div className="muted">
                    left: {contradiction.left_evidence_id ?? "unknown"}
                  </div>
                  <div className="muted">
                    right: {contradiction.right_evidence_id ?? "unknown"}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Section>
      </div>

      <Section title="Memory Records">
        {memory.memories.length === 0 ? (
          <div className="empty">No memory records</div>
        ) : (
          <ul className="timeline">
            {memory.memories.map(record => (
              <li key={record.memory_id} className="timeline-item">
                <div className="timeline-top">
                  <span>{record.memory_id}</span>
                  <span className="timeline-time">
                    {new Date(record.timestamp).toLocaleString()}
                  </span>
                </div>

                <div className="timeline-summary">{record.summary}</div>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <div className="grid grid-2">
        <Section title="Evidence References">
          {memory.evidence_refs.length === 0 ? (
            <div className="empty">None</div>
          ) : (
            <ul className="list">
              {memory.evidence_refs.map(evidenceId => (
                <li key={evidenceId}>
                  <a href={`/evidence/${evidenceId}`}>{evidenceId}</a>
                </li>
              ))}
            </ul>
          )}
        </Section>

        <Section title="Decisions">
          {memory.decisions.length === 0 ? (
            <div className="empty">None</div>
          ) : (
            <ul className="list">
              {memory.decisions.map(decisionId => (
                <li key={decisionId}>{decisionId}</li>
              ))}
            </ul>
          )}
        </Section>
      </div>

      <Section title="Knowledge Timeline">
        <EventTimeline items={memory.timeline} />
      </Section>
    </div>
  );
}
