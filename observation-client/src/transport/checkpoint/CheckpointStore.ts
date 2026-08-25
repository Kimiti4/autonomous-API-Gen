export interface CheckpointRecord<TState> {
  readonly streamId: string;
  /** Highest sequence applied at checkpoint time. */
  readonly sequence: number;
  readonly savedAt: number;
  readonly state: TState;
  /** SHA-256 of canonicalJson(state); integrity check on load. */
  readonly contentHash: string;
}

export interface CheckpointStore<TState> {
  save(record: CheckpointRecord<TState>): Promise<void>;
  load(streamId: string): Promise<CheckpointRecord<TState> | null>;
  clear(streamId: string): Promise<void>;
}