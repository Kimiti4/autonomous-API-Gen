export type EpistemicStatus =
  | "observed"
  | "inferred"
  | "unknown"
  | "contradiction";

export type Severity =
  | "debug"
  | "info"
  | "warning"
  | "error"
  | "fatal";

export type EventCategory =
  | "runtime"
  | "evidence"
  | "evolution"
  | "governance"
  | "knowledge";

export interface ObservatoryEvent {
  id: string;
  timestamp: string;
  source: string;
  category: EventCategory;
  type: string;
  subject_id: string;
  correlation_id?: string | null;
  causation_id?: string | null;
  payload: Record<string, unknown>;
  epistemic_status: EpistemicStatus;
  authorization?: string | null;
  evidence_refs: string[];
  provenance: Record<string, unknown>;
  severity: Severity;
}

export interface TimelineEntry {
  event_id: string;
  timestamp: string;
  category: EventCategory;
  type: string;
  subject_id: string;
  epistemic_status: EpistemicStatus;
  severity: Severity;
  summary: string;
}

export interface CurrentCycle {
  evolution_id: string;
  latest_event_type: string;
  updated_at: string;
}

export interface RuntimeState {
  processes: number;
  supervisors: number;
  messages_per_sec: number | string;
  memory_total: number | string;
  restart_count: number;
  health: string;
  updated_at: string | null;
}

export interface AuthorityState {
  interpretation: string;
  evolution: string;
  implementation: string;
  runtime: string;
  deployment: string;
  production: string;
  governance: string;
}

export interface GateState {
  gate: string;
  status: string;
}

export interface CommandActivity {
  requested: number;
  accepted: number;
  rejected: number;
}

export interface GovernanceState {
  current_authority: AuthorityState;
  active_gates: GateState[];
  safe_mode: string;
  human_controls: string[];
  command_activity: CommandActivity;
}

export interface OverviewState {
  current_cycle: CurrentCycle | null;
  status: string;
  runtime_health: string;
  safe_mode: string;
  evidence_count: number;
  authorization_state: string;
  recent_event_count: number;
}

export interface PipelineStage {
  stage: string;
  status: string;
}

export interface EpistemicCounts {
  observed: number;
  inferred: number;
  unknown: number;
  contradiction: number;
}

export interface EvolutionState {
  evolution_id: string;
  status: string;
  epistemic_state: EpistemicCounts;
  capability_check: Record<string, string>;
  pipeline: PipelineStage[];
  decision: string;
  authorization: AuthorityState;
  unknowns: string[];
  contradictions: string[];
  updated_at: string | null;
}

export interface EvidenceRecord {
  evidence_id: string;
  epistemic_status: EpistemicStatus;
  claim: string;
  result: string;
  scope: string[];
  not_proven: string[];
  provenance: Record<string, unknown>;
  observed_at: string | null;
}

export interface DashboardState {
  overview: OverviewState;
  runtime: RuntimeState;
  governance: GovernanceState;
  timeline: TimelineEntry[];
}

export interface ObservatorySearchQuery {
  q?: string;
  categories?: string[];
  severities?: string[];
  epistemic_statuses?: string[];
  since?: string;
  until?: string;
  limit?: number;
}

export interface ObservatorySearchResult {
  event_id: string;
  timestamp: string;
  category: string;
  type: string;
  subject_id: string;
  source: string;
  epistemic_status: EpistemicStatus;
  severity: Severity;
  entity_type: string;
  summary: string;
}

export interface SavedTrace {
  id: string;
  name: string;
  saved_at: string;
  params: ObservatorySearchQuery;
}

export interface ProvenanceSummary {
  subject_id: string;
  entity_type: string;
  latest_status: string;
  categories: string[];
  event_count: number;
  reference_count: number;
  warning_count: number;
  actors: string[];
  first_observed_at: string;
  last_observed_at: string;
}

export interface ProvenanceWarning {
  warning_id: string;
  timestamp: string;
  type: string;
  severity: string;
  event_type: string;
  subject_id: string;
  summary: string;
}

export interface ProvenanceNode {
  id: string;
  entity_type: string;
  event_count: number;
  last_observed_at: string | null;
}

export interface ProvenanceEdge {
  source: string;
  target: string;
  relation: string;
  event_id: string;
  timestamp: string;
}

export interface ProvenanceHashChainEntry {
  event_id: string;
  timestamp: string;
  event_hash: string;
  previous_event_hash: string | null;
}

export interface ProvenanceAudit {
  subject_id: string;
  entity_type: string;
  status: string;
  categories: string[];
  actors: string[];
  direct_event_count: number;
  related_event_count: number;
  epistemic_state: EpistemicCounts;
  evidence_refs: string[];
  hash_chain: ProvenanceHashChainEntry[];
  nodes: ProvenanceNode[];
  edges: ProvenanceEdge[];
  warnings: ProvenanceWarning[];
  governance_events: TimelineEntry[];
  timeline: TimelineEntry[];
  first_observed_at: string;
  last_observed_at: string;
}

export interface GenomeSummary {
  genome_id: string;
  status: string;
  candidate_id: string | null;
  generation: string | number | null;
  objective: string;
  pareto_state: string;
  chromosome_count: number;
  gene_count: number;
  mutation_count: number;
  crossover_count: number;
  selection_count: number;
  fitness_count: number;
  evidence_count: number;
  unknown_count: number;
  contradiction_count: number;
  updated_at: string | null;
}

export interface GenomeGene {
  gene_id: string;
  chromosome: string;
  value: unknown;
  previous_value: unknown;
  status: string;
  mutation_count: number;
  crossover_count: number;
  updated_at: string | null;
}

export interface GenomeChromosome {
  name: string;
  genes: GenomeGene[];
  gene_count: number;
  mutation_count: number;
  crossover_count: number;
  status: string;
}

export interface GenomeMutation {
  mutation_id: string;
  timestamp: string;
  chromosome: string | null;
  gene_id: string | null;
  previous_value: unknown;
  new_value: unknown;
  reason: string | null;
  evidence_refs: string[];
}

export interface GenomeCrossover {
  crossover_id: string;
  timestamp: string;
  chromosome: string | null;
  gene_id: string | null;
  parent_genome_ids: string[];
  evidence_refs: string[];
}

export interface GenomeSelection {
  selection_id: string;
  timestamp: string;
  candidate_id: string | null;
  outcome: unknown;
  reason: string | null;
  evidence_refs: string[];
}

export interface GenomeUnknown {
  unknown_id: string;
  question: string;
  timestamp: string;
}

export interface GenomeContradiction {
  contradiction_id: string;
  statement: string;
  timestamp: string;
}

export interface GenomeDetail {
  genome_id: string;
  status: string;
  candidate_id: string | null;
  generation: string | number | null;
  objective: string;
  description: string | null;
  environment: string | null;
  requirement_links: string[];
  pareto_state: string;
  epistemic_state: EpistemicCounts;
  chromosomes: GenomeChromosome[];
  genes: GenomeGene[];
  mutations: GenomeMutation[];
  crossovers: GenomeCrossover[];
  selections: GenomeSelection[];
  fitness_links: string[];
  evidence_refs: string[];
  unknowns: GenomeUnknown[];
  contradictions: GenomeContradiction[];
  timeline: TimelineEntry[];
  provenance: Record<string, unknown>;
  sources: string[];
  first_observed_at: string | null;
  updated_at: string | null;
}

export interface FitnessSummary {
  fitness_id: string;
  status: string;
  objective: string;
  pareto_state: string;
  metric_count: number;
  measurement_count: number;
  baseline_count: number;
  evaluation_count: number;
  evidence_count: number;
  unknown_count: number;
  contradiction_count: number;
  updated_at: string | null;
}

export interface FitnessMetric {
  metric_id: string;
  name: string;
  unit: string | null;
  direction: string | null;
  target_value: unknown;
  baseline_value: unknown;
  baseline_at: string | null;
  latest_value: unknown;
  latest_measurement_at: string | null;
  delta_vs_baseline: number | null;
  measurement_count: number;
  status: string;
}

export interface FitnessEvaluation {
  evaluation_id: string;
  timestamp: string;
  summary: string;
  result: unknown;
  evidence_refs: string[];
}

export interface FitnessUnknown {
  unknown_id: string;
  question: string;
  timestamp: string;
}

export interface FitnessContradiction {
  contradiction_id: string;
  statement: string;
  timestamp: string;
}

export interface FitnessDetail {
  fitness_id: string;
  status: string;
  objective: string;
  description: string | null;
  scope: string[];
  environment: string | null;
  candidate_id: string | null;
  implementation_id: string | null;
  deployment_id: string | null;
  pareto_state: string;
  epistemic_state: EpistemicCounts;
  metrics: FitnessMetric[];
  evaluations: FitnessEvaluation[];
  unknowns: FitnessUnknown[];
  contradictions: FitnessContradiction[];
  evidence_refs: string[];
  timeline: TimelineEntry[];
  provenance: Record<string, unknown>;
  sources: string[];
  first_observed_at: string | null;
  updated_at: string | null;
}

export interface ExperimentSummary {
  experiment_id: string;
  status: string;
  authorization_state: string;
  reproducibility: string;
  hypothesis: string | null;
  fixture: string | null;
  environment: string | null;
  evidence_count: number;
  results_count: number;
  unknown_count: number;
  contradiction_count: number;
  updated_at: string | null;
}

export interface ExperimentResult {
  result_id: string;
  timestamp: string;
  name: string;
  expected: unknown;
  observed: unknown;
  passed: unknown;
  epistemic_status: EpistemicStatus;
  evidence_refs: string[];
}

export interface ExperimentUnknown {
  unknown_id: string;
  question: string;
  timestamp: string;
}

export interface ExperimentContradiction {
  contradiction_id: string;
  statement: string;
  timestamp: string;
}

export interface ExperimentDetail {
  experiment_id: string;
  status: string;
  authorization_state: string;
  reproducibility: string;
  hypothesis: string | null;
  objective: string | null;
  fixture: string | null;
  environment: string | null;
  run_id: string | null;
  deployment_id: string | null;
  implementation_id: string | null;
  candidate_id: string | null;
  scope: string[];
  epistemic_state: EpistemicCounts;
  results: ExperimentResult[];
  unknowns: ExperimentUnknown[];
  contradictions: ExperimentContradiction[];
  evidence_refs: string[];
  timeline: TimelineEntry[];
  provenance: Record<string, unknown>;
  sources: string[];
  first_observed_at: string | null;
  updated_at: string | null;
}

export interface KnowledgeSubjectSummary {
  subject_id: string;
  status: string;
  summary: string;
  epistemic_state: EpistemicCounts;
  categories: string[];
  evidence_count: number;
  updated_at: string | null;
}

export interface KnowledgeFact {
  fact_id: string;
  statement: string;
  epistemic_status: EpistemicStatus;
  evidence_refs: string[];
  timestamp: string;
  source: string;
  severity: Severity;
}

export interface KnowledgeUnknown {
  unknown_id: string;
  question: string;
  reason: string;
  timestamp: string;
}

export interface KnowledgeContradiction {
  contradiction_id: string;
  statement: string;
  left_evidence_id?: string | null;
  right_evidence_id?: string | null;
  timestamp: string;
}

export interface KnowledgeMemoryRecord {
  memory_id: string;
  timestamp: string;
  summary: string;
  memory: unknown;
}

export interface KnowledgeMemory {
  subject_id: string;
  status: string;
  epistemic_state: EpistemicCounts;
  facts: KnowledgeFact[];
  unknowns: KnowledgeUnknown[];
  contradictions: KnowledgeContradiction[];
  memories: KnowledgeMemoryRecord[];
  evidence_refs: string[];
  decisions: string[];
  timeline: TimelineEntry[];
  provenance: Record<string, unknown>;
  sources: string[];
  first_observed_at: string | null;
  updated_at: string | null;
}
