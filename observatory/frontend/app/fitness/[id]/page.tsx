"use client";

import { useCallback, useEffect, useState } from "react";

import {
  EventTimeline,
  KeyValue,
  Section,
  StatusPill
} from "@/components";
import { api } from "@/lib/api";
import type { FitnessDetail, FitnessMetric } from "@/lib/types";

function displayValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "unknown";
  }

  if (typeof value === "object") {
    return JSON.stringify(value);
  }

  return String(value);
}

function MetricCard({ metric }: { metric: FitnessMetric }) {
  return (
    <li className="timeline-item">
      <div className="timeline-top">
        <span>{metric.name}</span>
        <StatusPill status={metric.status} />
      </div>

      <div className="timeline-meta">
        <span>unit {displayValue(metric.unit)}</span>
        <span>direction {displayValue(metric.direction)}</span>
        <span>measurements {metric.measurement_count}</span>
      </div>

      <div style={{ height: 8 }} />

      <KeyValue
        data={{
          latest_value: displayValue(metric.latest_value),
          baseline_value: displayValue(metric.baseline_value),
          target_value: displayValue(metric.target_value),
          delta_vs_baseline: displayValue(metric.delta_vs_baseline),
          latest_measurement_at: displayValue(metric.latest_measurement_at),
          baseline_at: displayValue(metric.baseline_at)
        }}
      />
    </li>
  );
}

export default function FitnessDetailPage({
  params
}: {
  params: { id: string };
}) {
  const [fitness, setFitness] = useState<FitnessDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const nextFitness = await api.fitnessDetail(params.id);
      setFitness(nextFitness);
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

  if (error && !fitness) {
    return <div className="error">Fitness detail unavailable: {error}</div>;
  }

  if (!fitness) {
    return <div className="muted">Loading fitness detail…</div>;
  }

  return (
    <div className="grid">
      {error ? <div className="error">{error}</div> : null}

      <Section
        title={`Fitness ${fitness.fitness_id}`}
        right={<StatusPill status={fitness.status} />}
      >
        <KeyValue
          data={{
            objective: fitness.objective,
            pareto_state: fitness.pareto_state,
            environment: displayValue(fitness.environment),
            updated_at: displayValue(fitness.updated_at),
            first_observed_at: displayValue(fitness.first_observed_at)
          }}
        />
      </Section>

      <Section title="Description">
        {fitness.description ? (
          <div>{fitness.description}</div>
        ) : (
          <div className="empty">No description recorded</div>
        )}
      </Section>

      <Section title="Scope">
        {fitness.scope.length === 0 ? (
          <div className="empty">No scope recorded</div>
        ) : (
          <ul className="list">
            {fitness.scope.map(scopeItem => (
              <li key={scopeItem}>{scopeItem}</li>
            ))}
          </ul>
        )}
      </Section>

      <div className="grid grid-2">
        <Section title="Execution Lineage">
          <KeyValue
            data={{
              candidate_id: displayValue(fitness.candidate_id),
              implementation_id: displayValue(fitness.implementation_id),
              deployment_id: displayValue(fitness.deployment_id)
            }}
          />
        </Section>

        <Section title="Epistemic State">
          <KeyValue data={fitness.epistemic_state} />
        </Section>
      </div>

      <Section title="Metrics">
        {fitness.metrics.length === 0 ? (
          <div className="empty">No metrics recorded</div>
        ) : (
          <ul className="timeline">
            {fitness.metrics.map(metric => (
              <MetricCard key={metric.metric_id} metric={metric} />
            ))}
          </ul>
        )}
      </Section>

      <Section title="Evaluations">
        {fitness.evaluations.length === 0 ? (
          <div className="empty">No evaluations recorded</div>
        ) : (
          <ul className="timeline">
            {fitness.evaluations.map(evaluation => (
              <li key={evaluation.evaluation_id} className="timeline-item">
                <div className="timeline-top">
                  <span>{evaluation.evaluation_id}</span>
                  <span className="timeline-time">
                    {new Date(evaluation.timestamp).toLocaleString()}
                  </span>
                </div>

                <div className="timeline-summary">{evaluation.summary}</div>

                <div className="timeline-meta">
                  <span>result {displayValue(evaluation.result)}</span>
                  <span>evidence {evaluation.evidence_refs.length}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <div className="grid grid-2">
        <Section title="Unknowns">
          {fitness.unknowns.length === 0 ? (
            <div className="empty">None</div>
          ) : (
            <ul className="list">
              {fitness.unknowns.map(unknown => (
                <li key={unknown.unknown_id}>{unknown.question}</li>
              ))}
            </ul>
          )}
        </Section>

        <Section title="Contradictions">
          {fitness.contradictions.length === 0 ? (
            <div className="empty">None</div>
          ) : (
            <ul className="list">
              {fitness.contradictions.map(contradiction => (
                <li key={contradiction.contradiction_id}>
                  {contradiction.statement}
                </li>
              ))}
            </ul>
          )}
        </Section>
      </div>

      <Section title="Evidence References">
        {fitness.evidence_refs.length === 0 ? (
          <div className="empty">None</div>
        ) : (
          <ul className="list">
            {fitness.evidence_refs.map(evidenceId => (
              <li key={evidenceId}>
                <a href={`/evidence/${evidenceId}`}>{evidenceId}</a>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Fitness Timeline">
        <EventTimeline items={fitness.timeline} />
      </Section>
    </div>
  );
}
