import {
  HttpObservationClient,
  IndexedDbCheckpointStore,
  LiveProjection,
  MemoryCheckpointStore,
  WebSocketEventStream,
  initialUiState,
  observationReducer,
  type ObservationUiState,
} from '@esap/observation-client';
import type { DashboardRuntimeConfig } from './configLoader';

export interface ObservationClientBundle {
  projection: LiveProjection<ObservationUiState>;
  http: HttpObservationClient<ObservationUiState>;
}

export function createObservationClients(
  config: DashboardRuntimeConfig,
  onStatusChange?: (status: import('@esap/observation-client').ProjectionStatus) => void,
): ObservationClientBundle {
  const http = new HttpObservationClient<ObservationUiState>({
    baseUrl: config.observationApiPath,
    streamId: config.streamId,
    credentials: 'same-origin', // GAP-05: cookie auth only; tokens never in URLs
  });

  const checkpointStore =
    typeof indexedDB !== 'undefined'
      ? new IndexedDbCheckpointStore<ObservationUiState>('esap-dashboard', 'projection')
      : new MemoryCheckpointStore<ObservationUiState>();

  const wsUrl = `${location.origin.replace(/^http/, 'ws')}${config.observationWsPath}?streamId=${encodeURIComponent(config.streamId)}`;

  const projection = new LiveProjection<ObservationUiState>({
    streamId: config.streamId,
    initialState: initialUiState(),
    reducer: observationReducer,
    snapshotSource: http,
    replaySource: http,
    eventStream: new WebSocketEventStream({ url: wsUrl }),
    checkpointStore,
    onStatusChange,
    livenessProbe: async () => {
      try {
        const res = await fetch(`${config.observationApiPath}/capabilities`, {
          credentials: 'same-origin',
        });
        return res.ok;
      } catch {
        return false;
      }
    },
  });

  return { projection, http };
}
