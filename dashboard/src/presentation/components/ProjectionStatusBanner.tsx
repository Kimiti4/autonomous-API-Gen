import { useSyncExternalStore } from 'react';
import {
  getProjectionStatus,
  subscribeProjectionStatus,
} from '@/application/statusStore';
import type { ProjectionStatus } from '@esap/observation-client';
import { useRuntimeConfig } from '@/presentation/contexts/ConfigContext';

const STATE_STYLES: Record<string, string> = {
  initializing: 'bg-slate-200 text-slate-700',
  healthy: 'bg-emerald-100 text-emerald-800',
  degraded: 'bg-amber-100 text-amber-900',
  stale: 'bg-orange-100 text-orange-900',
  desynchronized: 'bg-red-100 text-red-900',
  unavailable: 'bg-red-200 text-red-950',
};

export function ProjectionStatusBanner(): JSX.Element | null {
  const config = useRuntimeConfig();
  const status = useSyncExternalStore(subscribeProjectionStatus, getProjectionStatus);

  if (status === null) return null;

  const style = STATE_STYLES[status.state] ?? STATE_STYLES.initializing;
  const isAuthError = status.lastError?.code === 'SEC_UNAUTHENTICATED';

  return (
    <div
      data-testid="projection-banner"
      className={`px-4 py-2 text-sm font-medium ${style}`}
      role="status"
    >
      <span>Stream: {status.streamId}</span>
      <span className="mx-2">·</span>
      <span>
        applied {status.appliedSequence} / authoritative {status.authoritativeSequence}
      </span>
      {isAuthError && (
        <a href={config.authLoginPath} className="ml-3 underline">
          Sign in to continue observing
        </a>
      )}
      {!isAuthError && status.state !== 'healthy' && (
        <span className="ml-3">Last error: {status.lastError?.message ?? 'n/a'}</span>
      )}
    </div>
  );
}

export type { ProjectionStatus };
