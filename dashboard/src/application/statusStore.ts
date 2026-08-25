import type { ProjectionStatus } from '@esap/observation-client';

type Listener = () => void;

let current: ProjectionStatus | null = null;
const listeners = new Set<Listener>();

export function setProjectionStatus(status: ProjectionStatus): void {
  current = status;
  for (const listener of listeners) listener();
}

export function getProjectionStatus(): ProjectionStatus | null {
  return current;
}

export function subscribeProjectionStatus(listener: Listener): () => void {
  listeners.add(listener);
  return () => { listeners.delete(listener); };
}

/** Test hook. */
export function resetProjectionStatus(): void {
  current = null;
  listeners.clear();
}
