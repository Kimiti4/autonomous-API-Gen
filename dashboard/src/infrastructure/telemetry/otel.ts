let enabled = false;

/**
 * OpenTelemetry Web SDK bootstrap (lazy, optional).
 * The dashboard never gates rendering on telemetry availability.
 */
export async function initTelemetry(opts: {
  serviceName: string;
  otlpTracesEndpoint?: string;
  otlpMetricsEndpoint?: string;
}): Promise<boolean> {
  if (!opts.otlpTracesEndpoint && !opts.otlpMetricsEndpoint) return false;
  try {
    const webSdk = await import('@opentelemetry/sdk-trace-web');
    const resources = await import('@opentelemetry/resources');
    const semantic = await import('@opentelemetry/semantic-conventions');
    const exporterTraces = await import('@opentelemetry/exporter-trace-otlp-http');

    const resource = new resources.Resource({
      [semantic.ATTR_SERVICE_NAME]: opts.serviceName,
    });

    const provider = new webSdk.WebTracerProvider({ resource });
    if (opts.otlpTracesEndpoint) {
      provider.addSpanProcessor(
        new webSdk.BatchSpanProcessor(
          new exporterTraces.OTLPTraceExporter({ url: opts.otlpTracesEndpoint }),
        ),
      );
    }
    provider.register();
    enabled = true;
    return true;
  } catch {
    return false; // telemetry is best-effort by design
  }
}

export function isTelemetryEnabled(): boolean {
  return enabled;
}
