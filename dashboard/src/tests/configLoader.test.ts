import { describe, expect, it, vi } from 'vitest';
import { loadRuntimeConfig } from '@/application/configLoader';

function fetchJson(body: unknown, ok = true): typeof fetch {
  return vi.fn(async () =>
    new Response(JSON.stringify(body), {
      status: ok ? 200 : 500,
      headers: { 'Content-Type': 'application/json' },
    }),
  ) as unknown as typeof fetch;
}

describe('loadRuntimeConfig', () => {
  it('merges served config over safe same-origin defaults', async () => {
    const cfg = await loadRuntimeConfig(
      '/config/runtime.json',
      fetchJson({ observationApiPath: '/obs', streamId: 's2', enableTelemetry: true }),
    );
    expect(cfg.observationApiPath).toBe('/obs');
    expect(cfg.streamId).toBe('s2');
    expect(cfg.enableTelemetry).toBe(true);
    expect(cfg.authLoginPath).toBe('/auth/login');
  });

  it('returns defaults when the config endpoint fails', async () => {
    const cfg = await loadRuntimeConfig('/config/runtime.json', fetchJson({}, false));
    expect(cfg.observationApiPath).toBe('/observation');
    expect(cfg.streamId).toBe('evolution-main');
  });

  it('returns defaults when the network throws', async () => {
    const failing = vi.fn(async () => {
      throw new TypeError('network down');
    }) as unknown as typeof fetch;
    const cfg = await loadRuntimeConfig('/config/runtime.json', failing);
    expect(cfg.enableTelemetry).toBe(false);
  });
});
