import type { ContractMetadata, ObservationProvenance } from './provenance.js';

export type ErrorCategory =
  | 'client' | 'platform' | 'contract' | 'synchronization' | 'security' | 'resource';

export type ErrorSeverity = 'info' | 'warning' | 'error' | 'fatal';

export type ErrorCode =
  | 'CLIENT_INVALID_REQUEST' | 'CLIENT_MISSING_PARAMETER' | 'CLIENT_INVALID_CONTRACT_VERSION'
  | 'SEC_UNAUTHENTICATED' | 'SEC_UNAUTHORIZED' | 'SEC_TOKEN_EXPIRED' | 'SEC_FORBIDDEN_RESOURCE'
  | 'CONTRACT_DEPRECATED' | 'CONTRACT_UNSUPPORTED_VERSION' | 'CONTRACT_SCHEMA_MISMATCH'
  | 'SYNC_SEQUENCE_GAP' | 'SYNC_STREAM_NOT_FOUND' | 'SYNC_CHECKPOINT_UNAVAILABLE'
  | 'SYNC_REPLAY_EXHAUSTED' | 'SYNC_DESYNCHRONIZED'
  | 'PLATFORM_INTERNAL' | 'PLATFORM_UNAVAILABLE' | 'PLATFORM_DEGRADED' | 'PLATFORM_MAINTENANCE'
  | 'RESOURCE_RATE_LIMITED' | 'RESOURCE_QUOTA_EXCEEDED' | 'RESOURCE_NOT_FOUND'
  | 'RESOURCE_CONCURRENT_MODIFICATION';

export type RecoveryAction =
  | 'none' | 'retry_immediately' | 'retry_with_backoff' | 'resync_stream'
  | 'renegotiate_contract' | 'authenticate' | 'failover' | 'halt_and_report';

export interface RecoveryGuidance {
  readonly action: RecoveryAction;
  readonly retryAfterSeconds?: number;
  readonly alternativeEndpoint?: string;
  readonly resyncFromSequence?: number;
  readonly requiredContractVersion?: string;
  readonly message: string;
}

export interface ObservationError {
  readonly code: ErrorCode;
  readonly category: ErrorCategory;
  readonly severity: ErrorSeverity;
  readonly message: string;
  readonly occurredAt: string;
  readonly traceId?: string;
}

export interface ErrorContext {
  readonly contractId?: string;
  readonly operation?: string;
  readonly parameters?: Readonly<Record<string, unknown>>;
  readonly streamId?: string;
  readonly sequence?: number;
}

export interface ErrorEnvelope {
  readonly metadata: ContractMetadata;
  readonly error: ObservationError;
  readonly context?: ErrorContext;
  readonly recovery: RecoveryGuidance;
  readonly provenance: ObservationProvenance;
}