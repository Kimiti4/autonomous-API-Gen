import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ProjectionStatusBanner } from '@/presentation/components/ProjectionStatusBanner';
import { resetProjectionStatus, setProjectionStatus } from '@/application/statusStore';
import type { ProjectionStatus } from '@esap/observation-client';

vi.mock('@/presentation/contexts/ConfigContext', () => ({
  useRuntimeConfig: () => ({
    observationApiPath: '/observation',
    observationWsPath: '/ws/evolution',
    streamId: 'evolution-main',
    enableTelemetry: false,
    serviceName: 'esap-dashboard',
    authLoginPath: '/auth/login',
  }),
}));

function status(overrides: Partial<ProjectionStatus> = {}): ProjectionStatus {
  return {
    state: 'healthy',
    streamId: 'evolution-main',
    authoritativeSequence: 10,
    appliedSequence: 9,
    lastSuccessfulSyncAt: null,
    lastEventAt: null,
    lastError: null,
    ...overrides,
  };
}

describe('ProjectionStatusBanner', () => {
  it('renders nothing before the first status arrives', () => {
    resetProjectionStatus();
    const { container } = render(<ProjectionStatusBanner />);
    expect(container).toBeEmptyDOMElement();
  });

  it('shows sequences and a login link on SEC_UNAUTHENTICATED', () => {
    resetProjectionStatus();
    setProjectionStatus(
      status({
        state: 'unavailable',
        appliedSequence: 4,
        authoritativeSequence: 5,
        lastError: {
          category: 'security',
          severity: 'error',
          code: 'SEC_UNAUTHENTICATED',
          message: 'authentication required',
          occurredAt: new Date().toISOString(),
        },
      }),
    );
    render(<ProjectionStatusBanner />);
    expect(screen.getByTestId('projection-banner')).toHaveTextContent('applied 4');
    expect(screen.getByRole('link', { name: /sign in/i })).toHaveAttribute(
      'href',
      '/auth/login',
    );
  });

  it('shows the error message for non-auth failures', () => {
    resetProjectionStatus();
    setProjectionStatus(
      status({
        state: 'stale',
        lastError: {
          category: 'synchronization',
          severity: 'warning',
          code: 'SYNC_DESYNCHRONIZED',
          message: 'no heartbeat for 60s',
          occurredAt: new Date().toISOString(),
        },
      }),
    );
    render(<ProjectionStatusBanner />);
    expect(screen.getByTestId('projection-banner')).toHaveTextContent(/no heartbeat for 60s/);
  });
});
