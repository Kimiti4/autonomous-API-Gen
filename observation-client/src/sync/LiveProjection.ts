import type { EvolutionEventEnvelope } from '../contracts/envelope.js';
import { EventTypes } from '../contracts/envelope.js';
import type { ObservationError } from '../contracts/errors.js';
import type {
  EventStream,
  ReplaySource,
  SnapshotSource,
  StreamLifecycle,
  Unsubscribe,
} from '../transport/ports.js';
import type {
  CheckpointRecord,
  CheckpointStore,
} from '../transport/checkpoint/CheckpointStore.js';
import { AsyncMutex } from '../util/mutex.js';
import { canonicalJson, sha256Hex } from '../util/hash.js';
import { DuplicateGuard } from './DuplicateGuard.js';
import { SequenceTracker } from './SequenceTracker.js';
import { GapDetector, type EnvelopeVerdict } from './GapDetector.js';
import { RecoveryCoordinator } from './RecoveryCoordinator.js';
import type { ProjectionHealth, ProjectionStatus } from '../health/ProjectionStatus.js';
import {
  ObservationCounters,
  type MetricsSink,
  type ObservationMetrics,
} from '../telemetry/counters.js';

export type ProjectionReducer<TState, TPayload> = (
  state: TState,
  envelope: EvolutionEventEnvelope<TPayload>,
) => TState;

export interface LiveProjectionOptions {
  readonly staleAfterMs?: number;
  readonly checkpointIntervalMs?: number;
  readonly maxCheckpointAgeMs?: number;
  readonly maxRecoveryAttempts?: number;
  readonly duplicateGuardCapacity?: number;
  readonly heartbeatEventType?: string;
  readonly stalenessPollMs?: number;
}

export interface LiveProjectionConfig<TState, TPayload> {
  readonly streamId: string;
  readonly initialState: TState;
  readonly reducer: ProjectionReducer<TState, TPayload>;
  readonly snapshotSource: SnapshotSource<TState>;
  readonly replaySource: ReplaySource<TPayload>;
  readonly eventStream: EventStream<TPayload>;
  readonly checkpointStore?: CheckpointStore<TState>;
  readonly livenessProbe?: () => Promise<boolean>;
  readonly options?: LiveProjectionOptions;
  readonly onStatusChange?: (status: ProjectionStatus) => void;
  readonly metricsSink?: MetricsSink;
}

const DEFAULTS = {
  staleAfterMs: 30_000,
  checkpointIntervalMs: 5_000,
  maxCheckpointAgeMs: 24 * 60 * 60 * 1000,
  maxRecoveryAttempts: 3,
  duplicateGuardCapacity: 10_000,
  heartbeatEventType: EventTypes.Heartbeat,
  stalenessPollMs: 5_000,
} as const;

/**
 * The synchronization primitive. Framework-agnostic.
 *
 * Invariants:
 *  - Never silently advances past a gap.
 *  - Never recomputes authoritative facts; only applies platform events.
 *  - All state mutation is serialized by a mutex.
 */
export class LiveProjection<TState, TPayload = unknown> {
  private readonly config: LiveProjectionConfig<TState, TPayload>;
  private readonly options: Required<LiveProjectionOptions>;
  private readonly mutex = new AsyncMutex();
  private readonly tracker = new SequenceTracker();
  private readonly duplicates: DuplicateGuard;
  private readonly detector: GapDetector;
  private readonly coordinator: RecoveryCoordinator<TState, TPayload>;
  private readonly counters = new ObservationCounters();

  private state: TState;
  private authoritativeSequence = -1;
  private lastEventAtMs: number | null = null;
  private lastError: ObservationError | null = null;
  private lastSuccessfulSyncAt: string | null = null;
  private health: ProjectionHealth = 'initializing';
  private recoveryAttempts = 0;
  private started = false;

  private subscribers = new Set<(state: TState) => void>();
  private unsubEnvelope: Unsubscribe | null = null;
  private unsubLifecycle: Unsubscribe | null = null;
  private stalenessTimer: ReturnType<typeof setInterval> | null = null;
  private checkpointTimer: ReturnType<typeof setInterval> | null = null;
  private lastCheckpointAtMs = 0;

  constructor(config: LiveProjectionConfig<TState, TPayload>) {
    this.config = config;
    this.options = { ...DEFAULTS, ...(config.options ?? {}) };
    this.state = config.initialState;
    this.duplicates = new DuplicateGuard(this.options.duplicateGuardCapacity);
    this.detector = new GapDetector(this.duplicates, this.tracker);
    this.coordinator = new RecoveryCoordinator(config.replaySource, config.snapshotSource);
  }

  // ---------- Public API ----------

  async start(): Promise<void> {
    if (this.started) return;
    this.started = true;
    this.setHealth('initializing');

    const resumed = await this.tryResumeFromCheckpoint();
    if (!resumed) {
      await this.hydrateFromSnapshot();
    }

    this.unsubEnvelope = this.config.eventStream.onEnvelope((envelope) => {
      void this.onEnvelope(envelope);
    });
    this.unsubLifecycle = this.config.eventStream.onLifecycle((state) => {
      this.onLifecycle(state);
    });

    await this.config.eventStream.connect();
    this.startStalenessMonitor();
    this.startCheckpointLoop();
    if (this.health === 'initializing') this.setHealth('healthy');
  }

  async stop(): Promise<void> {
    if (!this.started) return;
    this.started = false;
    if (this.stalenessTimer) clearInterval(this.stalenessTimer);
    if (this.checkpointTimer) clearInterval(this.checkpointTimer);
    this.stalenessTimer = null;
    this.checkpointTimer = null;
    this.unsubEnvelope?.();
    this.unsubLifecycle?.();
    this.unsubEnvelope = null;
    this.unsubLifecycle = null;
    await this.checkpoint();
    this.config.eventStream.close();
  }

  getState(): TState {
    return this.state;
  }

  getStatus(): ProjectionStatus {
    return {
      state: this.health,
      streamId: this.config.streamId,
      authoritativeSequence: this.authoritativeSequence,
      appliedSequence: this.tracker.appliedSequence,
      lastSuccessfulSyncAt: this.lastSuccessfulSyncAt,
      lastEventAt: this.lastEventAtMs === null ? null : new Date(this.lastEventAtMs).toISOString(),
      lastError: this.lastError,
    };
  }

  subscribe(handler: (state: TState) => void): Unsubscribe {
    this.subscribers.add(handler);
    return () => this.subscribers.delete(handler);
  }

  metrics(): ObservationMetrics {
    return this.counters.snapshot();
  }

  async checkpoint(): Promise<void> {
    const store = this.config.checkpointStore;
    if (!store) return;
    const state = this.state;
    const contentHash = await sha256Hex(canonicalJson(state));
    const record: CheckpointRecord<TState> = {
      streamId: this.config.streamId,
      sequence: this.tracker.appliedSequence,
      savedAt: Date.now(),
      state,
      contentHash,
    };
    await store.save(record);
    this.lastCheckpointAtMs = Date.now();
  }

  // ---------- Hydration ----------

  private async tryResumeFromCheckpoint(): Promise<boolean> {
    const store = this.config.checkpointStore;
    if (!store) return false;

    let record: CheckpointRecord<TState> | null;
    try {
      record = await store.load(this.config.streamId);
    } catch {
      return false;
    }
    if (!record) return false;

    if (Date.now() - record.savedAt > this.options.maxCheckpointAgeMs) {
      await store.clear(this.config.streamId).catch(() => undefined);
      return false;
    }

    const hash = await sha256Hex(canonicalJson(record.state));
    if (hash !== record.contentHash) {
      await store.clear(this.config.streamId).catch(() => undefined);
      return false;
    }

    // Adopt checkpoint state, then catch up via replay.
    this.state = record.state;
    this.tracker.setFromConsistencyPoint(record.sequence);
    this.duplicates.reset();
    try {
      await this.catchUpFrom(record.sequence);
      return true;
    } catch {
      return false; // fall back to full snapshot
    }
  }

  private async catchUpFrom(after: number): Promise<void> {
    const result = await this.config.replaySource.recover(after);
    for (const envelope of result.replayEvents) {
      this.applyEnvelopeDirect(envelope);
    }
    this.authoritativeSequence = Math.max(
      this.authoritativeSequence,
      this.tracker.appliedSequence,
    );
    this.lastSuccessfulSyncAt = new Date().toISOString();
  }

  private async hydrateFromSnapshot(): Promise<void> {
    const snapshot = await this.coordinator.snapshotState();
    this.counters.snapshotFetches += 1;
    this.state = snapshot.state;
    this.tracker.setFromConsistencyPoint(snapshot.sequence);
    this.duplicates.reset();
    this.authoritativeSequence = snapshot.sequence;
    this.lastSuccessfulSyncAt = new Date().toISOString();
    this.touchLiveness();
  }

  // ---------- Event handling ----------

  private onEnvelope(envelope: EvolutionEventEnvelope<TPayload>): void {
    void this.mutex.runExclusive(async () => {
      const verdict = this.detector.evaluate(envelope.eventId, envelope.sequence);

      if (verdict.kind === 'duplicate') {
        this.counters.duplicatesIgnored += 1;
        return;
      }

      if (verdict.kind === 'gap') {
        await this.recover(verdict, envelope);
        return;
      }

      this.applyEnvelope(envelope);
    });
  }

  /** Apply an expected envelope. Serialized by the caller. */
  private applyEnvelope(envelope: EvolutionEventEnvelope<TPayload>): void {
    // AM-1: heartbeats consume sequence + update liveness, but never touch state.
    if (envelope.eventType === this.options.heartbeatEventType) {
      this.tracker.advance();
      this.duplicates.markProcessed(envelope.eventId);
      this.counters.heartbeats += 1;
      this.touchLiveness();
      return;
    }

    try {
      this.state = this.config.reducer(this.state, envelope);
    } catch (error) {
      // Reducer failure = projection bug; do not advance, mark desynchronized.
      this.lastError = this.toObservationError(error, 'Reducer failed');
      this.setHealth('desynchronized');
      return;
    }

    this.tracker.advance();
    this.duplicates.markProcessed(envelope.eventId);
    this.authoritativeSequence = Math.max(this.authoritativeSequence, envelope.sequence);
    this.counters.eventsApplied += 1;
    this.touchLiveness();
    this.notifySubscribers();
    this.maybeCheckpoint();
  }

  /** Apply replay events during recovery; asserts consecutiveness. */
  private applyEnvelopeDirect(envelope: EvolutionEventEnvelope<TPayload>): void {
    const verdict = this.detector.evaluate(envelope.eventId, envelope.sequence);
    if (verdict.kind === 'duplicate') {
      this.counters.duplicatesIgnored += 1;
      return;
    }
    if (verdict.kind === 'gap') {
      throw new Error(`Replay discontinuity at sequence ${envelope.sequence}`);
    }
    this.applyEnvelope(envelope);
    this.counters.replayedEvents += 1;
  }

  // ---------- Recovery ----------

  private async recover(
    gap: { missingFrom: number; received: number },
    pending: EvolutionEventEnvelope<TPayload>,
  ): Promise<void> {
    this.counters.gapsDetected += 1;

    if (this.recoveryAttempts >= this.options.maxRecoveryAttempts) {
      this.setHealth('desynchronized');
      return;
    }
    this.recoveryAttempts += 1;

    try {
      const plan = await this.coordinator.plan(gap.missingFrom);

      if (plan.kind === 'resync') {
        await this.hydrateFromSnapshot();
        // Pending envelope is now stale (covered by snapshot). Drop it.
        this.recoveryAttempts = 0;
        this.setHealth('healthy');
        return;
      }

      // Adopt consistency point, apply replay, then the pending envelope.
      this.tracker.setFromConsistencyPoint(plan.consistencySequence);
      for (const event of plan.events) {
        this.applyEnvelopeDirect(event);
      }
      this.applyEnvelopeDirect(pending);

      this.recoveryAttempts = 0;
      this.counters.recoveriesSucceeded += 1;
      this.lastSuccessfulSyncAt = new Date().toISOString();
      this.setHealth('healthy');
    } catch (error) {
      this.counters.recoveriesFailed += 1;
      this.lastError = this.toObservationError(error, 'Recovery failed');
      if (this.recoveryAttempts >= this.options.maxRecoveryAttempts) {
        this.setHealth('desynchronized');
      } else {
        this.setHealth('degraded');
      }
    }
  }

  // ---------- Lifecycle & health ----------

  private onLifecycle(state: StreamLifecycle): void {
    switch (state) {
      case 'open':
        this.counters.streamReconnects += 1;
        if (this.health === 'unavailable' || this.health === 'degraded') {
          this.setHealth('healthy');
        }
        break;
      case 'reconnecting':
        this.counters.streamDisconnects += 1;
        if (this.health !== 'desynchronized') this.setHealth('degraded');
        break;
      case 'closed':
        if (this.health !== 'desynchronized') this.setHealth('unavailable');
        break;
      case 'connecting':
        break;
    }
  }

  private startStalenessMonitor(): void {
    this.stalenessTimer = setInterval(() => {
      void this.checkStaleness();
    }, this.options.stalenessPollMs);
  }

  private async checkStaleness(): Promise<void> {
    if (this.health !== 'healthy' && this.health !== 'stale') return;
    if (this.lastEventAtMs === null) return;

    const idle = Date.now() - this.lastEventAtMs;
    if (idle <= this.options.staleAfterMs) {
      if (this.health === 'stale') this.setHealth('healthy');
      return;
    }

    if (this.config.livenessProbe) {
      try {
        const alive = await this.config.livenessProbe();
        if (alive) return; // platform is quiet but alive → stay healthy
      } catch {
        // fall through to stale
      }
    }
    this.setHealth('stale');
  }

  private startCheckpointLoop(): void {
    if (!this.config.checkpointStore) return;
    this.checkpointTimer = setInterval(() => {
      void this.checkpoint().catch(() => undefined);
    }, this.options.checkpointIntervalMs);
  }

  private maybeCheckpoint(): void {
    if (!this.config.checkpointStore) return;
    if (Date.now() - this.lastCheckpointAtMs >= this.options.checkpointIntervalMs) {
      void this.checkpoint().catch(() => undefined);
    }
  }

  // ---------- Helpers ----------

  private touchLiveness(): void {
    this.lastEventAtMs = Date.now();
    if (this.health === 'stale') this.setHealth('healthy');
  }

  private setHealth(health: ProjectionHealth): void {
    if (this.health === health) return;
    this.health = health;
    this.config.onStatusChange?.(this.getStatus());
    if (this.config.metricsSink) this.config.metricsSink.record(this.metrics());
  }

  private notifySubscribers(): void {
    for (const handler of this.subscribers) handler(this.state);
  }

  private toObservationError(error: unknown, fallback: string): ObservationError {
    const message = error instanceof Error ? error.message : fallback;
    return {
      code: 'PLATFORM_INTERNAL',
      category: 'platform',
      severity: 'error',
      message,
      occurredAt: new Date().toISOString(),
    };
  }
}