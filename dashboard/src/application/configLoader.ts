export interface DashboardRuntimeConfig {
  observationApiPath: string;
  observationWsPath: string;
  streamId: string;
  enableTelemetry: boolean;
  otlpTracesEndpoint?: string;
  otlpMetricsEndpoint?: string;
  serviceName: string;
  authLoginPath: string;
}

const DEFAULTS: DashboardRuntimeConfig = {
  observationApiPath: '/observation',
  observationWsPath: '/ws/evolution',
  streamId: 'evolution-main',
  enableTelemetry: false,
  serviceName: 'esap-dashboard',
  authLoginPath: '/auth/login',
};

/** Runtime configuration served by nginx / K8s ConfigMap — NOT build-time env. */
export async function loadRuntimeConfig(
  path = '/config/runtime.json',
  fetchImpl: typeof fetch = fetch,
): Promise<DashboardRuntimeConfig> {
  try {
    const res = await fetchImpl(path, { cache: 'no-store', credentials: 'same-origin' });
    if (!res.ok) return DEFAULTS;
    const partial = (await res.json()) as Partial<DashboardRuntimeConfig>;
    return { ...DEFAULTS, ...partial };
  } catch {
    return DEFAULTS; // same-origin defaults are safe; config is not a security boundary
  }
}
