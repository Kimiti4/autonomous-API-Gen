"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Section, StatusPill } from "@/components";
import { api } from "@/lib/api";
import type { GenomeSummary } from "@/lib/types";

export default function GenomesPage() {
  const [items, setItems] = useState<GenomeSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");

  const refresh = useCallback(async () => {
    try {
      const nextItems = await api.genomes();
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
    return <div className="error">Genomes unavailable: {error}</div>;
  }

  if (!items) {
    return <div className="muted">Loading genomes…</div>;
  }

  const normalizedFilter = filter.trim().toLowerCase();

  const visibleItems =
    normalizedFilter.length === 0
      ? items
      : items.filter(item =>
          item.genome_id.toLowerCase().includes(normalizedFilter)
        );

  return (
    <div className="grid">
      {error ? <div className="error">{error}</div> : null}

      <Section title="Evolution Genomes">
        <input
          value={filter}
          onChange={event => setFilter(event.target.value)}
          placeholder="Filter genomes"
        />

        <div style={{ height: 12 }} />

        {visibleItems.length === 0 ? (
          <div className="empty">
            No genomes visible. Emit genome events to populate this view.
          </div>
        ) : (
          <ul className="timeline">
            {visibleItems.map(item => (
              <li key={item.genome_id} className="timeline-item">
                <div className="timeline-top">
                  <Link href={`/genomes/${item.genome_id}`}>
                    {item.genome_id}
                  </Link>

                  <StatusPill status={item.status} />
                </div>

                <div className="timeline-summary">{item.objective}</div>

                <div className="timeline-meta">
                  <span>candidate {item.candidate_id ?? "unknown"}</span>
                  <span>generation {item.generation ?? "unknown"}</span>
                  <span>pareto {item.pareto_state}</span>
                  <span>chromosomes {item.chromosome_count}</span>
                  <span>genes {item.gene_count}</span>
                  <span>mutations {item.mutation_count}</span>
                  <span>crossovers {item.crossover_count}</span>
                  <span>selections {item.selection_count}</span>
                  <span>fitness links {item.fitness_count}</span>
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
