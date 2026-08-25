import { useEffect, useMemo, useState } from 'react';
import { LiveProjection, type ObservationUiState, type ProjectionStatus } from '@esap/observation-client';
import type { ObservationMetrics } from '@esap/observation-client';
import { createObservationClients, type ObservationClientBundle } from '@/application/observationClient';
import { setProjectionStatus } from '@/application/statusStore';
import { useRuntimeConfig } from '@/presentation/contexts/ConfigContext';

export interface ProjectionView {
  state: ObservationUiState;
  status: ProjectionStatus | null;
  metrics: () => ObservationMetrics;
  projection: LiveProjection<ObservationUiState> | null;
}

const EMPTY_VIEW: ProjectionView = {
  state: { facets: {}, meta: { generation: -1, facetUpdatedAt: {} } },
  status: null,
  metrics: () => ({
    eventsApplied: 0,
    duplicatesIgnored: 0,
    gapsDetected: 0,
    recoveriesSucceeded: 0,
    recoveriesFailed: 0,
    replayedEvents: 0,
    snapshotFetches: 0,
    streamDisconnects: 0,
    streamReconnects: 0,
    heartbeats: 0,
  }),
  projection: null,
};

export function useProjection(): ProjectionView {
  const config = useRuntimeConfig();
  const [bundle, setBundle] = useState<ObservationClientBundle | null>(null);
  const [state, setState] = useState<ObservationUiState>(EMPTY_VIEW.state);
  const [status, setStatus] = useState<ProjectionStatus | null>(null);

  useEffect(() => {
    let unsubState: (() => void) | undefined;
    const clients = createObservationClients(config, (s) => {
      setStatus(s);
      setProjectionStatus(s);
    });
    setBundle(clients);
    unsubState = clients.projection.subscribe(setState);
    setStatus(clients.projection.getStatus());
    void clients.projection.start();
    return () => {
      unsubState?.();
      void clients.projection.stop();
      setBundle(null);
    };
  }, [config]);

  return useMemo(
    () => ({
      state,
      status,
      metrics: () => bundle?.projection.metrics() ?? EMPTY_VIEW.metrics(),
      projection: bundle?.projection ?? null,
    }),
    [state, status, bundle],
  );
}
