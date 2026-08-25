import type { CheckpointRecord, CheckpointStore } from './CheckpointStore.js';

export class MemoryCheckpointStore<TState> implements CheckpointStore<TState> {
  private readonly records = new Map<string, CheckpointRecord<TState>>();

  async save(record: CheckpointRecord<TState>): Promise<void> {
    this.records.set(record.streamId, record);
  }

  async load(streamId: string): Promise<CheckpointRecord<TState> | null> {
    return this.records.get(streamId) ?? null;
  }

  async clear(streamId: string): Promise<void> {
    this.records.delete(streamId);
  }
}