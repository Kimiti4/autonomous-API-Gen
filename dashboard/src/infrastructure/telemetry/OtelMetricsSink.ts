import { initTelemetry } from './otel';
import type { MetricsSink, ObservationMetrics } from '@esap/observation-client';

const METRIC_NAMES = [
  'eventsApplied',
  'duplicatesIgnored',
  'gapsDetected',
  'recoveriesSucceeded',
  'recoveriesFailed',
  'replayedEvents',
  'snapshotFetches',
  'streamDisconnects',
  'streamReconnects',
  'heartbeats',
] as const;

type MetricName = (typeof METRIC_NAMES)[number];

/**
 * Bridges LiveProjection's ObservationMetrics into the OpenTelemetry
 * metrics API. Each observable gauge reads the latest recorded value.
 */
export class OtelMetricsSink implements MetricsSink {
  private readonly latest: Partial<Record<MetricName, number>> = {};

  constructor(serviceName: string) {
    void this.bootstrap(serviceName);
  }

  private async bootstrap(serviceName: string): Promise<void> {
    const ok = await initTelemetry({ serviceName });
    if (!ok) return;
    try {
      const api = await import('@opentelemetry/api');
      const meter = api.metrics.getMeter(serviceName);
      for (const name of METRIC_NAMES) {
        const gauge = meter.createObservableGauge(`esap.observation.${name}`);
        gauge.addCallback((result) => {
          const value = this.latest[name];
          if (value != null) result.observe(value);
        });
      }
    } catch {
      // telemetry unavailable — sink becomes a no-op
    }
  }

  /** Called by ProjectionProvider on every status change / poll. */
  record(metrics: ObservationMetrics): void {
    for (const name of METRIC_NAMES) {
      const value = metrics[name];
      if (value == null) continue;
      this.latest[name] = value;
    }
  }

  snapshot(): Readonly<Partial<Record<MetricName, number>>> {
    return this.latest;
  }
}
