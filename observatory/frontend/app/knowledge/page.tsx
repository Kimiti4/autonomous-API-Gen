"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Section, StatusPill } from "@/components";
import { api } from "@/lib/api";
import type { KnowledgeSubjectSummary } from "@/lib/types";

export default function KnowledgePage() {
  const [items, setItems] = useState<KnowledgeSubjectSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");

  const refresh = useCallback(async () => {
    try {
      const nextItems = await api.knowledgeOverview();
      setItems(nextItems);
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

  if (error && !items) {
    return <div className="error">Knowledge unavailable: {error}</div>;
  }

  if (!items) {
    return <div className="muted">Loading knowledge…</div>;
  }

  const normalizedFilter = filter.trim().toLowerCase();

  const visibleItems =
    normalizedFilter.length === 0
      ? items
      : items.filter(item =>
          item.subject_id.toLowerCase().includes(normalizedFilter)
        );

  return (
    <div className="grid">
      {error ? <div className="error">{error}</div> : null}

      <Section title="Knowledge / Memory">
        <input
          value={filter}
          onChange={event => setFilter(event.target.value)}
          placeholder="Filter knowledge subjects"
        />

        <div style={{ height: 12 }} />

        {visibleItems.length === 0 ? (
          <div className="empty">
            No knowledge subjects visible. Emit knowledge or memory events to
            populate this view.
          </div>
        ) : (
          <ul className="timeline">
            {visibleItems.map(item => (
              <li key={item.subject_id} className="timeline-item">
                <div className="timeline-top">
                  <Link href={`/knowledge/${item.subject_id}`}>
                    {item.subject_id}
                  </Link>

                  <StatusPill status={item.status} />
                </div>

                <div className="timeline-summary">{item.summary}</div>

                <div className="timeline-meta">
                  <span>observed {item.epistemic_state.observed}</span>
                  <span>inferred {item.epistemic_state.inferred}</span>
                  <span>unknown {item.epistemic_state.unknown}</span>
                  <span>
                    contradictions {item.epistemic_state.contradiction}
                  </span>
                  <span>evidence {item.evidence_count}</span>
                  <span>categories {item.categories.join(", ")}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Section>
    </div>
  );
}
