import type { ContractMetadata, ObservationProvenance } from './provenance.js';
import type { EvolutionEventEnvelope } from './envelope.js';

export interface RecoveryResult<TPayload = unknown> {
  /**
   * AM-3 (normative): `state` is the materialized state AS OF `sequence`.
   * Applying `replayEvents` (ascending; each sequence > `sequence`) yields
   * the current state.
   */
  readonly state: Readonly<Record<string, unknown>>;
  readonly sequence: number;
  readonly replayEvents: readonly EvolutionEventEnvelope<TPayload>[];
}

/** AM-4: hydration wrapper — current state + its stream sequence. */
export interface ObservationSnapshotWrapper<TData> {
  readonly data: TData;
  readonly streamId: string;
  readonly sequence: number;
}

export interface CapabilitySchema {
  readonly contractId: string;
  readonly versions: readonly string[];
}

export interface CapabilityFeature {
  readonly id: string;
  readonly version: string;
}

export interface CapabilityContract {
  readonly contractId: string;
  readonly schemaVersion: string;
  readonly observationSchemas: readonly CapabilitySchema[];
  readonly eventTypes: readonly string[];
  readonly supportedStreamIds: readonly string[];
  readonly features: readonly CapabilityFeature[];
}

// Re-exported for consumer convenience; keeps provenance types co-visible.
export type { ContractMetadata, ObservationProvenance };

// ---------------------------------------------------------------------------
// Flattened observation projections — TypeScript mirrors of the platform's
// app/core/contracts/observations.py (single source of truth: the platform).
// ---------------------------------------------------------------------------

export interface DomainSummary {
  readonly name: string;
  readonly capabilityCount: number;
}

export interface ServiceSummary {
  readonly id: string;
  readonly name: string;
  readonly domain: string;
}

export interface DeploymentTargetSummary {
  readonly target: string;
  readonly serviceCount: number;
}

/** GET /observation/isr — flattened ISR observation. */
export interface ISRObservation {
  readonly metadata?: ContractMetadata;
  readonly provenance?: ObservationProvenance;
  readonly isrRevision: string;
  readonly domains: ReadonlyArray<DomainSummary>;
  readonly services: ReadonlyArray<ServiceSummary>;
  readonly deploymentTargets: ReadonlyArray<DeploymentTargetSummary>;
}

export type ObjectiveDirection = 'maximize' | 'minimize';

export interface FitnessObjective {
  readonly dimension: string;
  readonly direction: ObjectiveDirection;
  readonly normalization: string;
}

export interface CandidateFitness {
  readonly candidateId: string;
  readonly scores: Readonly<Record<string, number>>;
  /** AUTHORITATIVE: computed by the platform; clients never recompute. */
  readonly isOnParetoFrontier: boolean;
}

/** GET /observation/fitness?generation= — authoritative Pareto report. */
export interface FitnessReport {
  readonly metadata?: ContractMetadata;
  readonly provenance?: ObservationProvenance;
  readonly generation: number;
  readonly evaluatedAt: string;
  readonly objectives: ReadonlyArray<FitnessObjective>;
  readonly candidates: ReadonlyArray<CandidateFitness>;
  readonly paretoFrontierCandidateIds: ReadonlyArray<string>;
}