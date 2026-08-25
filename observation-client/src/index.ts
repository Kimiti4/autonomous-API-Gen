// Contracts
export type {
  ContractMetadata,
  ObservationProvenance,
} from './contracts/provenance.js';
export type {
  ErrorEnvelope,
  ObservationError,
  ErrorContext,
  RecoveryGuidance,
  ErrorCode,
  ErrorCategory,
  ErrorSeverity,
  RecoveryAction,
} from './contracts/errors.js';
export type {
  EvolutionEventEnvelope,
  EventSource,
  EventIntegrity,
  EventType,
} from './contracts/envelope.js';
export { EventTypes } from './contracts/envelope.js';
export type {
  RecoveryResult,
  ObservationSnapshotWrapper,
  CapabilityContract,
  CapabilitySchema,
  CapabilityFeature,
} from './contracts/observations.js';
export type {
  ISRObservation,
  FitnessReport,
  DomainSummary,
  ServiceSummary,
  DeploymentTargetSummary,
  FitnessObjective,
  CandidateFitness,
} from './contracts/observations.js';
export type {
  GovernanceProjection,
  GovernanceDecision,
  CandidateGovernanceProjection,
} from './contracts/governance.js';
export type {
  CandidateLineage,
  OriginSpecView,
  EvolutionOperationView,
  FitnessEvaluationView,
  VerificationView,
  DeploymentView,
  OperationalFeedbackView,
} from './contracts/lineage.js';
export type { EvidenceRecord } from './contracts/evidence.js';

// Transport
export type {
  SnapshotSource,
  SnapshotResult,
  ReplaySource,
  ReplayResult,
  EventStream,
  StreamLifecycle,
  Unsubscribe,
} from './transport/ports.js';
export { HttpObservationClient, type HttpObservationConfig } from './transport/httpClient.js';
export {
  WebSocketEventStream,
  type WebSocketEventStreamConfig,
} from './transport/webSocketEventStream.js';
export { ObservationApiError } from './transport/errors.js';
export type {
  CheckpointStore,
  CheckpointRecord,
} from './transport/checkpoint/CheckpointStore.js';
export { MemoryCheckpointStore } from './transport/checkpoint/MemoryCheckpointStore.js';
export { IndexedDbCheckpointStore } from './transport/checkpoint/IndexedDbCheckpointStore.js';

// Sync
export {
  LiveProjection,
  type LiveProjectionConfig,
  type LiveProjectionOptions,
  type ProjectionReducer,
} from './sync/LiveProjection.js';
export { SequenceTracker, type SequenceVerdict } from './sync/SequenceTracker.js';
export { DuplicateGuard } from './sync/DuplicateGuard.js';
export { GapDetector, type EnvelopeVerdict } from './sync/GapDetector.js';
export { RecoveryCoordinator, type RecoveryPlan } from './sync/RecoveryCoordinator.js';
export { LruSet } from './sync/LruSet.js';

// UI projection state (reducer fold — equivalence-certified vs reducer_vectors)
export {
  observationReducer,
  initialUiState,
  type ObservationUiState,
} from './reducer.js';

// Health & telemetry
export type { ProjectionStatus, ProjectionHealth } from './health/ProjectionStatus.js';
export {
  ObservationCounters,
  type ObservationMetrics,
  type MetricsSink,
} from './telemetry/counters.js';

// Util
export { canonicalJson, sha256Hex } from './util/hash.js';
export { AsyncMutex } from './util/mutex.js';