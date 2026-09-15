"use client";

import { useCallback, useEffect, useState } from "react";

import {
  EventTimeline,
  KeyValue,
  Section,
  StatusPill
} from "@/components";
import { api } from "@/lib/api";
import type { GenomeDetail, GenomeGene } from "@/lib/types";

function displayValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "unknown";
  }

  if (typeof value === "object") {
    return JSON.stringify(value);
  }

  return String(value);
}

function GeneRow({ gene }: { gene: GenomeGene }) {
  return (
    <li className="timeline-item">
      <div className="timeline-top">
        <span>{gene.gene_id}</span>
        <StatusPill status={gene.status} />
      </div>

      <div className="timeline-meta">
        <span>value {displayValue(gene.value)}</span>
        <span>previous {displayValue(gene.previous_value)}</span>
        <span>mutations {gene.mutation_count}</span>
        <span>crossovers {gene.crossover_count}</span>
      </div>
    </li>
  );
}

export default function GenomeDetailPage({
  params
}: {
  params: { id: string };
}) {
  const [genome, setGenome] = useState<GenomeDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const nextGenome = await api.genomeDetail(params.id);
      setGenome(nextGenome);
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

  if (error && !genome) {
    return <div className="error">Genome unavailable: {error}</div>;
  }

  if (!genome) {
    return <div className="muted">Loading genome…</div>;
  }

  return (
    <div className="grid">
      {error ? <div className="error">{error}</div> : null}

      <Section
        title={`Genome ${genome.genome_id}`}
        right={<StatusPill status={genome.status} />}
      >
        <KeyValue
          data={{
            candidate_id: displayValue(genome.candidate_id),
            generation: displayValue(genome.generation),
            pareto_state: genome.pareto_state,
            environment: displayValue(genome.environment),
            updated_at: displayValue(genome.updated_at),
            first_observed_at: displayValue(genome.first_observed_at)
          }}
        />
      </Section>

      <Section title="Objective">
        {genome.objective ? (
          <div>{genome.objective}</div>
        ) : (
          <div className="empty">No objective recorded</div>
        )}
      </Section>

      <Section title="Description">
        {genome.description ? (
          <div>{genome.description}</div>
        ) : (
          <div className="empty">No description recorded</div>
        )}
      </Section>

      <div className="grid grid-2">
        <Section title="Requirement Links">
          {genome.requirement_links.length === 0 ? (
            <div className="empty">None</div>
          ) : (
            <ul className="list">
              {genome.requirement_links.map(requirementId => (
                <li key={requirementId}>{requirementId}</li>
              ))}
            </ul>
          )}
        </Section>

        <Section title="Epistemic State">
          <KeyValue data={genome.epistemic_state} />
        </Section>
      </div>

      <Section title="Chromosomes">
        {genome.chromosomes.length === 0 ? (
          <div className="empty">No chromosomes recorded</div>
        ) : (
          <ul className="timeline">
            {genome.chromosomes.map(chromosome => (
              <li key={chromosome.name} className="timeline-item">
                <details>
                  <summary>
                    {chromosome.name} — {chromosome.gene_count} genes
                  </summary>

                  <div className="timeline-meta">
                    <span>mutations {chromosome.mutation_count}</span>
                    <span>crossovers {chromosome.crossover_count}</span>
                  </div>

                  <div style={{ height: 8 }} />

                  {chromosome.genes.length === 0 ? (
                    <div className="empty">No genes recorded</div>
                  ) : (
                    <ul className="timeline">
                      {chromosome.genes.map(gene => (
                        <GeneRow key={gene.gene_id} gene={gene} />
                      ))}
                    </ul>
                  )}
                </details>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Mutations">
        {genome.mutations.length === 0 ? (
          <div className="empty">No mutations recorded</div>
        ) : (
          <ul className="timeline">
            {genome.mutations.map(mutation => (
              <li key={mutation.mutation_id} className="timeline-item">
                <div className="timeline-top">
                  <span>{mutation.mutation_id}</span>
                  <span className="timeline-time">
                    {new Date(mutation.timestamp).toLocaleString()}
                  </span>
                </div>

                <div className="timeline-meta">
                  <span>chromosome {mutation.chromosome ?? "unknown"}</span>
                  <span>gene {mutation.gene_id ?? "unknown"}</span>
                  <span>previous {displayValue(mutation.previous_value)}</span>
                  <span>new {displayValue(mutation.new_value)}</span>
                  <span>evidence {mutation.evidence_refs.length}</span>
                </div>

                {mutation.reason ? (
                  <div className="timeline-summary">{mutation.reason}</div>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Crossovers">
        {genome.crossovers.length === 0 ? (
          <div className="empty">No crossovers recorded</div>
        ) : (
          <ul className="timeline">
            {genome.crossovers.map(crossover => (
              <li key={crossover.crossover_id} className="timeline-item">
                <div className="timeline-top">
                  <span>{crossover.crossover_id}</span>
                  <span className="timeline-time">
                    {new Date(crossover.timestamp).toLocaleString()}
                  </span>
                </div>

                <div className="timeline-meta">
                  <span>chromosome {crossover.chromosome ?? "unknown"}</span>
                  <span>gene {crossover.gene_id ?? "unknown"}</span>
                  <span>
                    parents {crossover.parent_genome_ids.join(", ") || "unknown"}
                  </span>
                  <span>evidence {crossover.evidence_refs.length}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Selections">
        {genome.selections.length === 0 ? (
          <div className="empty">No selections recorded</div>
        ) : (
          <ul className="timeline">
            {genome.selections.map(selection => (
              <li key={selection.selection_id} className="timeline-item">
                <div className="timeline-top">
                  <span>{selection.selection_id}</span>
                  <span className="timeline-time">
                    {new Date(selection.timestamp).toLocaleString()}
                  </span>
                </div>

                <div className="timeline-meta">
                  <span>candidate {selection.candidate_id ?? "unknown"}</span>
                  <span>outcome {displayValue(selection.outcome)}</span>
                  <span>evidence {selection.evidence_refs.length}</span>
                </div>

                {selection.reason ? (
                  <div className="timeline-summary">{selection.reason}</div>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </Section>

      <div className="grid grid-2">
        <Section title="Fitness Links">
          {genome.fitness_links.length === 0 ? (
            <div className="empty">None</div>
          ) : (
            <ul className="list">
              {genome.fitness_links.map(fitnessId => (
                <li key={fitnessId}>
                  <a href={`/fitness/${fitnessId}`}>{fitnessId}</a>
                </li>
              ))}
            </ul>
          )}
        </Section>

        <Section title="Evidence References">
          {genome.evidence_refs.length === 0 ? (
            <div className="empty">None</div>
          ) : (
            <ul className="list">
              {genome.evidence_refs.map(evidenceId => (
                <li key={evidenceId}>
                  <a href={`/evidence/${evidenceId}`}>{evidenceId}</a>
                </li>
              ))}
            </ul>
          )}
        </Section>
      </div>

      <div className="grid grid-2">
        <Section title="Unknowns">
          {genome.unknowns.length === 0 ? (
            <div className="empty">None</div>
          ) : (
            <ul className="list">
              {genome.unknowns.map(unknown => (
                <li key={unknown.unknown_id}>{unknown.question}</li>
              ))}
            </ul>
          )}
        </Section>

        <Section title="Contradictions">
          {genome.contradictions.length === 0 ? (
            <div className="empty">None</div>
          ) : (
            <ul className="list">
              {genome.contradictions.map(contradiction => (
                <li key={contradiction.contradiction_id}>
                  {contradiction.statement}
                </li>
              ))}
            </ul>
          )}
        </Section>
      </div>

      <Section title="Genome Timeline">
        <EventTimeline items={genome.timeline} />
      </Section>
    </div>
  );
}
