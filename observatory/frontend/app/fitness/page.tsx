"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Section, StatusPill } from "@/components";
import { api } from "@/lib/api";
import type { FitnessSummary } from "@/lib/types";

export default function FitnessPage() {
  const [items, setItems] = useState<FitnessSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");

  const refresh = useCallback(async () => {
    try {
      const nextItems = await api.fitness();
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
    return <div className="error">Fitness unavailable: {error}</div>;
  }

  if (!items) {
    return <div className="muted">Loading fitness…</div>;
  }

  const normalizedFilter = filter.trim().toLowerCase();

  const visibleItems =
    normalizedFilter.length === 0
      ? items
      : items.filter(item =>
          item.fitness_id.toLowerCase().includes(normalizedFilter)
        );

  return (
    <div className="grid">
      {error ? <div className="error">{error}</div> : null}

      <Section title="Fitness">
        <input
          value={filter}
          onChange={event => setFilter(event.target.value)}
          placeholder="Filter fitness objectives"
        />

        <div style={{ height: 12 }} />

        {visibleItems.length === 0 ? (
          <div className="empty">
            No fitness objectives visible. Emit fitness events to populate
            this view.
          </div>
        ) : (
          <ul className="timeline">
            {visibleItems.map(item => (
              <li key={item.fitness_id} className="timeline-item">
                <div className="timeline-top">
                  <Link href={`/fitness/${item.fitness_id}`}>
                    {item.fitness_id}
                  </Link>

                  <StatusPill status={item.status} />
                </div>

                <div className="timeline-summary">{item.objective}</div>

                <div className="timeline-meta">
                  <span>pareto {item.pareto_state}</span>
                  <span>metrics {item.metric_count}</span>
                  <span>measurements {item.measurement_count}</span>
                  <span>baselines {item.baseline_count}</span>
                  <span>evaluations {item.evaluation_count}</span>
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
