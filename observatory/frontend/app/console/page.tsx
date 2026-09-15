"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { EpistemicBadge, Section, ServerWorkspacePanel, StatusPill } from "@/components";
import { api } from "@/lib/api";
import { workspacesApi } from "@/lib/workspaces";
import type {
  ObservatorySearchQuery,
  ObservatorySearchResult,
  SavedTrace
} from "@/lib/types";

const SAVED_TRACES_KEY = "observatory.savedTraces";

function linkForResult(result: ObservatorySearchResult): string {
  const subject = result.subject_id;

  switch (result.entity_type) {
    case "knowledge":
      return `/knowledge/${subject}`;
    case "experiment":
      return `/experiments/${subject}`;
    case "fitness":
      return `/fitness/${subject}`;
    case "genome":
    case "gene":
      return `/genomes/${subject}`;
    case "governance":
      return "/governance";
    case "decision":
    case "requirement":
    case "capability":
    case "command":
    case "evolution":
    case "evidence":
    case "entity":
    default:
      return `/provenance/${subject}`;
  }
}

function parseCommaList(value: string): string[] {
  return value
    .split(",")
    .map(item => item.trim())
    .filter(Boolean);
}

export default function ConsolePage() {
  const [q, setQ] = useState("");
  const [categories, setCategories] = useState("");
  const [severities, setSeverities] = useState("");
  const [epistemicStatuses, setEpistemicStatuses] = useState("");
  const [since, setSince] = useState("");
  const [until, setUntil] = useState("");
  const [limit, setLimit] = useState(200);

  const [results, setResults] = useState<ObservatorySearchResult[] | null>(
    null
  );
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [traceName, setTraceName] = useState("");
  const [savedTraces, setSavedTraces] = useState<SavedTrace[]>([]);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(SAVED_TRACES_KEY);

      if (raw) {
        setSavedTraces(JSON.parse(raw));
      }
    } catch {
      setSavedTraces([]);
    }
  }, []);

  const currentParams: ObservatorySearchQuery = {
    q: q.trim() || undefined,
    categories: parseCommaList(categories),
    severities: parseCommaList(severities),
    epistemic_statuses: parseCommaList(epistemicStatuses),
    since: since.trim() || undefined,
    until: until.trim() || undefined,
    limit
  };

  const runSearch = useCallback(async () => {
    setBusy(true);
    setError(null);

    try {
      const nextResults = await api.search(currentParams);
      setResults(nextResults);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Search failed");
    } finally {
      setBusy(false);
    }
  }, [
    q,
    categories,
    severities,
    epistemicStatuses,
    since,
    until,
    limit
  ]);

  useEffect(() => {
    runSearch();
  }, [runSearch]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const workspaceId = params.get("workspace");

    if (!workspaceId) {
      return;
    }

    workspacesApi
      .get(workspaceId)
      .then(workspace => {
        setQ(workspace.query.q ?? "");
        setCategories((workspace.query.categories ?? []).join(", "));
        setSeverities((workspace.query.severities ?? []).join(", "));
        setEpistemicStatuses(
          (workspace.query.epistemic_statuses ?? []).join(", ")
        );
        setSince(workspace.query.since ?? "");
        setUntil(workspace.query.until ?? "");
        setLimit(workspace.query.limit ?? 200);
      })
      .catch(() => {
        setError("Unable to load workspace");
      });
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const workspaceId = params.get("workspace");

    if (!workspaceId) {
      return;
    }

    workspacesApi
      .get(workspaceId)
      .then(workspace => {
        setQ(workspace.query.q ?? "");
        setCategories((workspace.query.categories ?? []).join(", "));
        setSeverities((workspace.query.severities ?? []).join(", "));
        setEpistemicStatuses(
          (workspace.query.epistemic_statuses ?? []).join(", ")
        );
        setSince(workspace.query.since ?? "");
        setUntil(workspace.query.until ?? "");
        setLimit(workspace.query.limit ?? 200);
      })
      .catch(() => {
        setError("Unable to load workspace");
      });
  }, []);

  function persistTraces(nextTraces: SavedTrace[]) {
    setSavedTraces(nextTraces);

    try {
      window.localStorage.setItem(
        SAVED_TRACES_KEY,
        JSON.stringify(nextTraces)
      );
    } catch {
      // Local trace persistence is best-effort.
    }
  }

  function saveTrace() {
    const name = traceName.trim() || `Trace ${new Date().toISOString()}`;

    const trace: SavedTrace = {
      id: crypto.randomUUID(),
      name,
      saved_at: new Date().toISOString(),
      params: currentParams
    };

    persistTraces([trace, ...savedTraces].slice(0, 25));
    setTraceName("");
  }

  function applyTrace(trace: SavedTrace) {
    setQ(trace.params.q ?? "");
    setCategories((trace.params.categories ?? []).join(", "));
    setSeverities((trace.params.severities ?? []).join(", "));
    setEpistemicStatuses((trace.params.epistemic_statuses ?? []).join(", "));
    setSince(trace.params.since ?? "");
    setUntil(trace.params.until ?? "");
    setLimit(trace.params.limit ?? 200);
  }

  function deleteTrace(traceId: string) {
    persistTraces(savedTraces.filter(trace => trace.id !== traceId));
  }

  return (
    <div className="grid">
      <Section title="Observatory Console">
        <div className="grid">
          <label className="grid">
            <span className="muted">Search</span>
            <input
              value={q}
              onChange={event => setQ(event.target.value)}
              placeholder="subject, type, source, payload text"
            />
          </label>

          <label className="grid">
            <span className="muted">Categories, comma-separated</span>
            <input
              value={categories}
              onChange={event => setCategories(event.target.value)}
              placeholder="runtime, evidence, evolution, governance, knowledge"
            />
          </label>

          <label className="grid">
            <span className="muted">Severities, comma-separated</span>
            <input
              value={severities}
              onChange={event => setSeverities(event.target.value)}
              placeholder="info, warning, error"
            />
          </label>

          <label className="grid">
            <span className="muted">Epistemic statuses, comma-separated</span>
            <input
              value={epistemicStatuses}
              onChange={event => setEpistemicStatuses(event.target.value)}
              placeholder="observed, inferred, unknown, contradiction"
            />
          </label>

          <div className="grid grid-2">
            <label className="grid">
              <span className="muted">Since, ISO timestamp</span>
              <input
                value={since}
                onChange={event => setSince(event.target.value)}
                placeholder="2026-01-01T00:00:00+00:00"
              />
            </label>

            <label className="grid">
              <span className="muted">Until, ISO timestamp</span>
              <input
                value={until}
                onChange={event => setUntil(event.target.value)}
                placeholder="2026-12-31T23:59:59+00:00"
              />
            </label>
          </div>

          <label className="grid">
            <span className="muted">Limit</span>
            <input
              type="number"
              min={1}
              max={1000}
              value={limit}
              onChange={event => setLimit(Number(event.target.value))}
            />
          </label>

          <div className="grid grid-2">
            <button onClick={runSearch} disabled={busy} type="button">
              {busy ? "Searching…" : "Search"}
            </button>

            <div className="grid grid-2">
              <a
                href={api.exportEventsUrl(currentParams, "json")}
                target="_blank"
                rel="noreferrer"
              >
                Export JSON
              </a>

              <a
                href={api.exportEventsUrl(currentParams, "csv")}
                target="_blank"
                rel="noreferrer"
              >
                Export CSV
              </a>
            </div>
          </div>
        </div>
      </Section>

      <Section title="Saved Traces">
        <div className="notice">
          Saved traces are stored locally in the browser. They are operator
          conveniences, not authoritative system evidence.
        </div>

        <div style={{ height: 12 }} />

        <div className="grid grid-2">
          <input
            value={traceName}
            onChange={event => setTraceName(event.target.value)}
            placeholder="Trace name"
          />

          <button onClick={saveTrace} type="button">
            Save current trace
          </button>
        </div>

        <div style={{ height: 12 }} />

        {savedTraces.length === 0 ? (
          <div className="empty">No saved traces</div>
        ) : (
          <ul className="timeline">
            {savedTraces.map(trace => (
              <li key={trace.id} className="timeline-item">
                <div className="timeline-top">
                  <span>{trace.name}</span>
                  <span className="timeline-time">
                    {new Date(trace.saved_at).toLocaleString()}
                  </span>
                </div>

                <div className="timeline-meta">
                  <span>query {trace.params.q ?? "none"}</span>
                  <span>
                    categories {(trace.params.categories ?? []).join(", ") || "any"}
                  </span>
                  <span>
                    severities {(trace.params.severities ?? []).join(", ") || "any"}
                  </span>
                </div>

                <div style={{ height: 8 }} />

                <div className="grid grid-2">
                  <button onClick={() => applyTrace(trace)} type="button">
                    Apply
                  </button>

                  <button onClick={() => deleteTrace(trace.id)} type="button">
                    Delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Server Workspaces">
        <ServerWorkspacePanel currentQuery={currentParams} />
      </Section>

      {error ? <div className="error">{error}</div> : null}

      <Section title="Results">
        {!results ? (
          <div className="muted">No search executed yet.</div>
        ) : results.length === 0 ? (
          <div className="empty">No results</div>
        ) : (
          <ul className="timeline">
            {results.map(result => (
              <li key={result.event_id} className="timeline-item">
                <div className="timeline-top">
                  <Link href={linkForResult(result)}>
                    {result.subject_id}
                  </Link>

                  <StatusPill status={result.severity} />
                </div>

                <div className="timeline-summary">{result.summary}</div>

                <div className="timeline-meta">
                  <EpistemicBadge status={result.epistemic_status} />
                  <span>category {result.category}</span>
                  <span>type {result.type}</span>
                  <span>entity {result.entity_type}</span>
                  <span>source {result.source}</span>
                  <span>
                    {new Date(result.timestamp).toLocaleString()}
                  </span>
                  <a
                    href={api.auditBundleUrl(result.subject_id)}
                    target="_blank"
                    rel="noreferrer"
                  >
                    audit bundle
                  </a>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Section>
    </div>
  );
}
