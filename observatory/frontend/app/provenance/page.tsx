"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Section, StatusPill } from "@/components";
import { api } from "@/lib/api";
import type { ProvenanceSummary } from "@/lib/types";

export default function ProvenancePage() {
  const [items, setItems] = useState<ProvenanceSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");

  const refresh = useCallback(async () => {
    try {
      const nextItems = await api.provenance();
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
    return <div className="error">Provenance unavailable: {error}</div>;
  }

  if (!items) {
    return <div className="muted">Loading provenance…</div>;
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

      <Section title="Provenance / Audit">
        <input
          value={filter}
          onChange={event => setFilter(event.target.value)}
          placeholder="Filter provenance subjects"
        />

        <div style={{ height: 12 }} />

        {visibleItems.length === 0 ? (
          <div className="empty">
            No provenance subjects visible. Emit events to populate this view.
          </div>
        ) : (
          <ul className="timeline">
            {visibleItems.map(item => (
              <li key={item.subject_id} className="timeline-item">
                <div className="timeline-top">
                  <Link href={`/provenance/${item.subject_id}`}>
                    {item.subject_id}
                  </Link>

                  <StatusPill status={item.latest_status} />
                </div>

                <div className="timeline-meta">
                  <span>type {item.entity_type}</span>
                  <span>events {item.event_count}</span>
                  <span>references {item.reference_count}</span>
                  <span>warnings {item.warning_count}</span>
                  <span>categories {item.categories.join(", ")}</span>
                  <span>
                    last observed{" "}
                    {new Date(item.last_observed_at).toLocaleString()}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Section>
    </div>
  );
}
