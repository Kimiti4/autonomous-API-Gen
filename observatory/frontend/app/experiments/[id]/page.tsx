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
import type { ExperimentDetail, ExperimentResult } from "@/lib/types";

function passedStatus(result: ExperimentResult): string {
  const passed = result.passed;

  if (passed === true || passed === "true" || passed === "pass") {
    return "pass";
  }

  if (passed === false || passed === "false" || passed === "fail") {
    return "fail";
  }

  return "unknown";
}

export default function ExperimentDetailPage({
  params
}: {
  params: { id: string };
}) {
  const [experiment, setExperiment] = useState<ExperimentDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const nextExperiment = await api.experiment(params.id);
      setExperiment(nextExperiment);
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

  if (error && !experiment) {
    return <div className="error">Experiment unavailable: {error}</div>;
  }

  if (!experiment) {
    return <div className="muted">Loading experiment…</div>;
  }

  return (
    <div className="grid">
      {error ? <div className="error">{error}</div> : null}

      <Section
        title={`Experiment ${experiment.experiment_id}`}
        right={<StatusPill status={experiment.status} />}
      >
        <KeyValue
          data={{
            authorization: experiment.authorization_state,
            reproducibility: experiment.reproducibility,
            fixture: experiment.fixture ?? "unknown",
            environment: experiment.environment ?? "unknown",
            updated_at: experiment.updated_at ?? "unknown",
            first_observed_at: experiment.first_observed_at ?? "unknown"
          }}
        />
      </Section>

      <Section title="Hypothesis">
        {experiment.hypothesis ? (
          <div>{experiment.hypothesis}</div>
        ) : (
          <div className="empty">No hypothesis recorded</div>
        )}
      </Section>

      <Section title="Objective">
        {experiment.objective ? (
          <div>{experiment.objective}</div>
        ) : (
          <div className="empty">No objective recorded</div>
        )}
      </Section>

      <div className="grid grid-2">
        <Section title="Execution Lineage">
          <KeyValue
            data={{
              run_id: experiment.run_id ?? "unknown",
              deployment_id: experiment.deployment_id ?? "unknown",
              implementation_id: experiment.implementation_id ?? "unknown",
              candidate_id: experiment.candidate_id ?? "unknown"
            }}
          />
        </Section>

        <Section title="Epistemic State">
          <KeyValue data={experiment.epistemic_state} />
        </Section>
      </div>

      <Section title="Scope">
        {experiment.scope.length === 0 ? (
          <div className="empty">No scope recorded</div>
        ) : (
          <ul className="list">
            {experiment.scope.map(scopeItem => (
              <li key={scopeItem}>{scopeItem}</li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Results">
        {experiment.results.length === 0 ? (
          <div className="empty">No results recorded</div>
        ) : (
          <ul className="timeline">
            {experiment.results.map(result => (
              <li key={result.result_id} className="timeline-item">
                <div className="timeline-top">
                  <span>{result.name}</span>
                  <StatusPill status={passedStatus(result)} />
                </div>

                <div className="timeline-meta">
                  <EpistemicBadge status={result.epistemic_status} />
                  <span>
                    expected:{" "}
                    {result.expected === null || result.expected === undefined
                      ? "unknown"
                      : String(result.expected)}
                  </span>
                  <span>
                    observed:{" "}
                    {result.observed === null || result.observed === undefined
                      ? "unknown"
                      : String(result.observed)}
                  </span>
                  <span>evidence {result.evidence_refs.length}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <div className="grid grid-2">
        <Section title="Unknowns">
          {experiment.unknowns.length === 0 ? (
            <div className="empty">None</div>
          ) : (
            <ul className="list">
              {experiment.unknowns.map(unknown => (
                <li key={unknown.unknown_id}>{unknown.question}</li>
              ))}
            </ul>
          )}
        </Section>

        <Section title="Contradictions">
          {experiment.contradictions.length === 0 ? (
            <div className="empty">None</div>
          ) : (
            <ul className="list">
              {experiment.contradictions.map(contradiction => (
                <li key={contradiction.contradiction_id}>
                  {contradiction.statement}
                </li>
              ))}
            </ul>
          )}
        </Section>
      </div>

      <Section title="Evidence References">
        {experiment.evidence_refs.length === 0 ? (
          <div className="empty">None</div>
        ) : (
          <ul className="list">
            {experiment.evidence_refs.map(evidenceId => (
              <li key={evidenceId}>
                <a href={`/evidence/${evidenceId}`}>{evidenceId}</a>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Experiment Timeline">
        <EventTimeline items={experiment.timeline} />
      </Section>
    </div>
  );
}
