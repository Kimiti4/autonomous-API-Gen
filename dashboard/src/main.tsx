import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import { ProjectionProvider } from '@/presentation/components/ProjectionProvider';
import { OtelMetricsSink } from '@/infrastructure/telemetry/OtelMetricsSink';
import { loadRuntimeConfig } from '@/application/configLoader';
import type { MetricsSink } from '@esap/observation-client';
import '@/index.css';

async function bootstrap(): Promise<void> {
  const config = await loadRuntimeConfig();
  let metricsSink: MetricsSink | null = null;
  if (config.enableTelemetry) {
    metricsSink = new OtelMetricsSink(config.serviceName);
  }

  const container = document.getElementById('root');
  if (container === null) throw new Error('Root container #root not found');

  createRoot(container).render(
    <StrictMode>
      <BrowserRouter>
        <ProjectionProvider>
          <App />
        </ProjectionProvider>
      </BrowserRouter>
    </StrictMode>,
  );

  // metricsSink is wired into LiveProjection by ProjectionProvider when
  // telemetry is enabled; kept here for the runtime reference.
  void metricsSink;
}

void bootstrap();
