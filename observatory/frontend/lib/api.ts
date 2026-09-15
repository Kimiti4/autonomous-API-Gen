import type {
  DashboardState,
  EvidenceRecord,
  EvolutionState,
  ExperimentDetail,
  ExperimentSummary,
  FitnessDetail,
  FitnessSummary,
  GenomeDetail,
  GenomeSummary,
  GovernanceState,
  KnowledgeMemory,
  KnowledgeSubjectSummary,
  ObservatorySearchQuery,
  ObservatorySearchResult,
  OverviewState,
  ProvenanceAudit,
  ProvenanceSummary,
  RuntimeState,
  TimelineEntry
} from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_OBSERVATORY_API_URL ?? "http://127.0.0.1:8000";

export const OBSERVATORY_API_BASE = API_BASE;

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    cache: "no-store",
    ...init
  });

  if (!response.ok) {
    let detail: unknown = response.statusText;

    try {
      const body = await response.json();
      detail = body.detail ?? body.error ?? body;
    } catch {
      // Keep the HTTP status text when the body is not JSON.
    }

    const message =
      typeof detail === "string" ? detail : JSON.stringify(detail);

    throw new ApiError(response.status, message);
  }

  return (await response.json()) as T;
}

export const api = {
  dashboard(): Promise<DashboardState> {
    return request<DashboardState>("/observatory/dashboard");
  },

  overview(): Promise<OverviewState> {
    return request<OverviewState>("/observatory/overview");
  },

  runtime(): Promise<RuntimeState> {
    return request<RuntimeState>("/observatory/runtime");
  },

  governance(): Promise<GovernanceState> {
    return request<GovernanceState>("/observatory/governance");
  },

  timeline(subject?: string, limit = 50): Promise<TimelineEntry[]> {
    const params = new URLSearchParams();

    if (subject) {
      params.set("subject", subject);
    }

    params.set("limit", String(limit));

    return request<TimelineEntry[]>(
      `/observatory/timeline?${params.toString()}`
    );
  },

  evolution(evolutionId: string): Promise<EvolutionState> {
    return request<EvolutionState>(
      `/observatory/evolution/${encodeURIComponent(evolutionId)}`
    );
  },

  evidence(evidenceId: string): Promise<EvidenceRecord> {
    return request<EvidenceRecord>(
      `/observatory/evidence/${encodeURIComponent(evidenceId)}`
    );
  },

  knowledgeOverview(): Promise<KnowledgeSubjectSummary[]> {
    return request<KnowledgeSubjectSummary[]>(
      "/observatory/knowledge/overview"
    );
  },

  knowledgeMemory(subjectId: string): Promise<KnowledgeMemory> {
    return request<KnowledgeMemory>(
      `/observatory/knowledge/${encodeURIComponent(subjectId)}/memory`
    );
  },

  experiments(): Promise<ExperimentSummary[]> {
    return request<ExperimentSummary[]>("/observatory/experiments");
  },

  experiment(experimentId: string): Promise<ExperimentDetail> {
    return request<ExperimentDetail>(
      `/observatory/experiments/${encodeURIComponent(experimentId)}`
    );
  },

  fitness(): Promise<FitnessSummary[]> {
    return request<FitnessSummary[]>("/observatory/fitness");
  },

  fitnessDetail(fitnessId: string): Promise<FitnessDetail> {
    return request<FitnessDetail>(
      `/observatory/fitness/${encodeURIComponent(fitnessId)}`
    );
  },

  genomes(): Promise<GenomeSummary[]> {
    return request<GenomeSummary[]>("/observatory/genomes");
  },

  genomeDetail(genomeId: string): Promise<GenomeDetail> {
    return request<GenomeDetail>(
      `/observatory/genomes/${encodeURIComponent(genomeId)}`
    );
  },

  provenance(): Promise<ProvenanceSummary[]> {
    return request<ProvenanceSummary[]>("/observatory/provenance");
  },

  provenanceAudit(subjectId: string): Promise<ProvenanceAudit> {
    return request<ProvenanceAudit>(
      `/observatory/provenance/${encodeURIComponent(subjectId)}`
    );
  },

  search(
    query: ObservatorySearchQuery
  ): Promise<ObservatorySearchResult[]> {
    const params = new URLSearchParams();

    if (query.q) {
      params.set("q", query.q);
    }

    if (query.categories && query.categories.length > 0) {
      params.set("categories", query.categories.join(","));
    }

    if (query.severities && query.severities.length > 0) {
      params.set("severities", query.severities.join(","));
    }

    if (query.epistemic_statuses && query.epistemic_statuses.length > 0) {
      params.set("epistemic_statuses", query.epistemic_statuses.join(","));
    }

    if (query.since) {
      params.set("since", query.since);
    }

    if (query.until) {
      params.set("until", query.until);
    }

    params.set("limit", String(query.limit ?? 200));

    return request<ObservatorySearchResult[]>(
      `/observatory/search?${params.toString()}`
    );
  },

  exportEventsUrl(
    query: ObservatorySearchQuery,
    format: "json" | "csv"
  ): string {
    const params = new URLSearchParams();

    if (query.q) {
      params.set("q", query.q);
    }

    if (query.categories && query.categories.length > 0) {
      params.set("categories", query.categories.join(","));
    }

    if (query.severities && query.severities.length > 0) {
      params.set("severities", query.severities.join(","));
    }

    if (query.epistemic_statuses && query.epistemic_statuses.length > 0) {
      params.set("epistemic_statuses", query.epistemic_statuses.join(","));
    }

    if (query.since) {
      params.set("since", query.since);
    }

    if (query.until) {
      params.set("until", query.until);
    }

    params.set("limit", String(query.limit ?? 500));
    params.set("format", format);

    return `${OBSERVATORY_API_BASE}/observatory/export/events?${params.toString()}`;
  },

  auditBundleUrl(subjectId: string): string {
    return `${OBSERVATORY_API_BASE}/observatory/audit-bundle/${encodeURIComponent(subjectId)}`;
  }
};
