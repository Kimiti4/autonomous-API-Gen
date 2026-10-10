import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MaintenanceOutboxPanel } from '@/presentation/components/MaintenanceOutboxPanel';
import { useObservationFetch } from '@/presentation/hooks/useObservationFetch';

vi.mock('@/presentation/hooks/useObservationFetch', () => ({
  useObservationFetch: vi.fn(),
}));

const mockedFetch = vi.mocked(useObservationFetch);

describe('MaintenanceOutboxPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders real queue counts and event delivery metadata', () => {
    mockedFetch.mockReturnValue({
      data: {
        status: 'available',
        summary: { pending: 1, delivering: 0, delivered: 3, dead_letter: 1 },
        items: [{
          event_digest: 'a'.repeat(64),
          status: 'dead_letter',
          attempts: 8,
          next_attempt_at: 10,
          lease_until: null,
          observatory_event_id: null,
          last_error: 'delivery-failed:TimeoutError',
          created_at: 1,
          updated_at: 2,
        }],
      },
      isLoading: false,
      isFetching: false,
      error: null,
      refetch: vi.fn(),
    } as never);

    render(<MaintenanceOutboxPanel />);
    expect(screen.getByText('Governed maintenance delivery')).toBeInTheDocument();
    expect(screen.getByText('Recently updated events')).toBeInTheDocument();
    expect(screen.getByText((_, element) => element?.tagName === 'P' && Boolean(element.textContent?.includes('delivery-failed:TimeoutError')))).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('dead letter')).toBeInTheDocument();
  });

  it('does not invent counts when the status endpoint is unavailable', () => {
    mockedFetch.mockReturnValue({
      data: undefined,
      isLoading: false,
      isFetching: false,
      error: new Error('Maintenance outbox status is temporarily unavailable.'),
      refetch: vi.fn(),
    } as never);

    render(<MaintenanceOutboxPanel />);
    expect(screen.getByRole('status')).toHaveTextContent('Maintenance delivery status is unavailable');
    expect(screen.queryByText('Recently updated events')).not.toBeInTheDocument();
  });
});
