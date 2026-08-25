export interface ObservationMetrics {
  readonly eventsApplied: number;
  readonly duplicatesIgnored: number;
  readonly gapsDetected: number;
  readonly recoveriesSucceeded: number;
  readonly recoveriesFailed: number;
  readonly replayedEvents: number;
  readonly snapshotFetches: number;
  readonly streamDisconnects: number;
  readonly streamReconnects: number;
  readonly heartbeats: number;
}

/** Dependency-free client-side counters; a MetricsSink can export them later. */
export class ObservationCounters {
  eventsApplied = 0;
  duplicatesIgnored = 0;
  gapsDetected = 0;
  recoveriesSucceeded = 0;
  recoveriesFailed = 0;
  replayedEvents = 0;
  snapshotFetches = 0;
  streamDisconnects = 0;
  streamReconnects = 0;
  heartbeats = 0;

  snapshot(): ObservationMetrics {
    return {
      eventsApplied: this.eventsApplied,
      duplicatesIgnored: this.duplicatesIgnored,
      gapsDetected: this.gapsDetected,
      recoveriesSucceeded: this.recoveriesSucceeded,
      recoveriesFailed: this.recoveriesFailed,
      replayedEvents: this.replayedEvents,
      snapshotFetches: this.snapshotFetches,
      streamDisconnects: this.streamDisconnects,
      streamReconnects: this.streamReconnects,
      heartbeats: this.heartbeats,
    };
  }
}

export interface MetricsSink {
  record(metrics: ObservationMetrics): void;
}