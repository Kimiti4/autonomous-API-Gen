import type {
  ReplayResult,
  ReplaySource,
  SnapshotResult,
  SnapshotSource,
} from './ports.js';
import { ObservationApiError } from './errors.js';
import type { EvolutionEventEnvelope } from '../contracts/envelope.js';
import type {
  ObservationSnapshotWrapper,
  RecoveryResult,
} from '../contracts/observations.js';

export interface HttpObservationConfig {
  /** Base path of the observation API, e.g. "/observation". */
  readonly baseUrl: string;
  readonly streamId: string;
  /** Cookie-based auth: never put tokens in the URL (GAP-05). */
  readonly credentials?: RequestCredentials;
  readonly replayLimit?: number;
  readonly headers?: Readonly<Record<string, string>>;
  readonly fetchImpl?: typeof fetch;
}

/**
 * Concrete HTTP adapter implementing SnapshotSource + ReplaySource against
 * the platform Observation API.
 */
export class HttpObservationClient<TState, TPayload = unknown>
  implements SnapshotSource<TState>, ReplaySource<TPayload>
{
  private readonly fetchImpl: typeof fetch;

  constructor(private readonly config: HttpObservationConfig) {
    this.fetchImpl = config.fetchImpl ?? fetch.bind(globalThis);
  }

  /** AM-4: expects ObservationSnapshotWrapper<TState>. */
  async fetch(): Promise<SnapshotResult<TState>> {
    const wrapper = await this.get<ObservationSnapshotWrapper<TState>>(
      `${this.config.baseUrl}/snapshot?streamId=${encodeURIComponent(this.config.streamId)}`,
    );
    return { state: wrapper.data, streamId: wrapper.streamId, sequence: wrapper.sequence };
  }

  async recover(after: number): Promise<ReplayResult<TPayload>> {
    const limit = this.config.replayLimit ?? 1000;
    const res = await this.get<RecoveryResult<TPayload>>(
      `${this.config.baseUrl}/state?streamId=${encodeURIComponent(this.config.streamId)}` +
        `&after=${after}&limit=${limit}`,
    );
    return {
      state: res.state,
      sequence: res.sequence,
      replayEvents: res.replayEvents as readonly EvolutionEventEnvelope<TPayload>[],
    };
  }

  private async get<T>(path: string): Promise<T> {
    const response = await this.fetchImpl(path, {
      method: 'GET',
      credentials: this.config.credentials ?? 'same-origin',
      headers: { Accept: 'application/json', ...(this.config.headers ?? {}) },
    });
    if (!response.ok) {
      throw await ObservationApiError.fromResponse(response);
    }
    return (await response.json()) as T;
  }
}