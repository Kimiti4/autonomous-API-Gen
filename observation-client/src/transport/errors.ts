import type { ErrorEnvelope, ErrorCode } from '../contracts/errors.js';

export class ObservationApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: ErrorCode | string,
    public readonly envelope: ErrorEnvelope | null,
    message: string,
  ) {
    super(message);
    this.name = 'ObservationApiError';
  }

  static async fromResponse(response: Response): Promise<ObservationApiError> {
    let envelope: ErrorEnvelope | null = null;
    try {
      envelope = (await response.json()) as ErrorEnvelope;
    } catch {
      envelope = null;
    }
    const code = envelope?.error?.code ?? 'PLATFORM_INTERNAL';
    const message = envelope?.error?.message ?? `HTTP ${response.status}`;
    return new ObservationApiError(response.status, code, envelope, message);
  }

  get isReplayExhausted(): boolean {
    return this.code === 'SYNC_REPLAY_EXHAUSTED';
  }

  get isStreamNotFound(): boolean {
    return this.code === 'SYNC_STREAM_NOT_FOUND';
  }
}