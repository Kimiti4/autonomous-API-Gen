export interface ContractMetadata {
  readonly contractId: string;
  readonly schemaVersion: string;
}

export interface ObservationProvenance {
  readonly sourceRevision: string;
  readonly sourceSubsystem: string;
  readonly capturedAt: string;
  readonly contentHash: string;
}