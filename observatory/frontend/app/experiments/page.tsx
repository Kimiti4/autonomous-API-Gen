"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Section, StatusPill } from "@/components";
import { api } from "@/lib/api";
import type { ExperimentSummary } from "@/lib/types";

export default function ExperimentsPage() {
  const [items, setItems] = useState<ExperimentSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");

  const refresh = useCallback(async () => {
    try {
      const nextItems = await api.experiments();
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
    return <div className="error">Experiments unavailable: {error}</div>;
  }

  if (!items) {
    return <div className="muted">Loading experiments…</div>;
  }

  const normalizedFilter = filter.trim().toLowerCase();

  const visibleItems =
    normalizedFilter.length === 0
      ? items
      : items.filter(item =>
          item.experiment_id.toLowerCase().includes(normalizedFilter)
        );

  return (
    <div className="grid">
      {error ? <div className="error">{error}</div> : null}

      <Section title="Experiments">
        <input
          value={filter}
          onChange={event => setFilter(event.target.value)}
          placeholder="Filter experiments"
        />

        <div style={{ height: 12 }} />

        {visibleItems.length === 0 ? (
          <div className="empty">
            No experiments visible. Emit experiment events to populate this
            view.
          </div>
        ) : (
          <ul className="timeline">
            {visibleItems.map(item => (
              <li key={item.experiment_id} className="timeline-item">
                <div className="timeline-top">
                  <Link href={`/experiments/${item.experiment_id}`}>
                    {item.experiment_id}
                  </Link>

                  <StatusPill status={item.status} />
                </div>

                <div className="timeline-summary">
                  {item.hypothesis ?? "No hypothesis recorded"}
                </div>

                <div className="timeline-meta">
                  <span>authorization {item.authorization_state}</span>
                  <span>reproducibility {item.reproducibility}</span>
                  <span>fixture {item.fixture ?? "unknown"}</span>
                  <span>environment {item.environment ?? "unknown"}</span>
                  <span>results {item.results_count}</span>
                  <span>evidence {item.evidence_count}</span>
                  <span>unknowns {item.unknown_count}</span>
                  <span>contradictions {item.contradiction_count}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Section>
    </div>
  );
}
