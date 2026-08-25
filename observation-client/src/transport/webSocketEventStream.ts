import type { EventStream, StreamLifecycle, Unsubscribe } from './ports.js';
import type { EvolutionEventEnvelope } from '../contracts/envelope.js';

export interface WebSocketEventStreamConfig {
  readonly url: string;
  readonly maxReconnectDelayMs?: number;
  readonly protocols?: string | string[];
}

/**
 * Reconnecting WebSocket transport.
 * - Authentication relies on cookies/headers via the gateway; NO token in URL.
 * - Transport reconnection is separate from state recovery (GapDetector).
 */
export class WebSocketEventStream<TPayload = unknown> implements EventStream<TPayload> {
  private socket: WebSocket | null = null;
  private envelopeHandlers = new Set<(e: EvolutionEventEnvelope<TPayload>) => void>();
  private lifecycleHandlers = new Set<(s: StreamLifecycle) => void>();
  private reconnectAttempt = 0;
  private closedByUser = false;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(private readonly config: WebSocketEventStreamConfig) {}

  async connect(): Promise<void> {
    this.closedByUser = false;
    this.open();
  }

  close(): void {
    this.closedByUser = true;
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.socket?.close();
    this.socket = null;
  }

  onEnvelope(handler: (e: EvolutionEventEnvelope<TPayload>) => void): Unsubscribe {
    this.envelopeHandlers.add(handler);
    return () => this.envelopeHandlers.delete(handler);
  }

  onLifecycle(handler: (s: StreamLifecycle) => void): Unsubscribe {
    this.lifecycleHandlers.add(handler);
    return () => this.lifecycleHandlers.delete(handler);
  }

  private open(): void {
    this.emitLifecycle('connecting');
    // Cookie-based auth: no query-string token.
    const socket = this.config.protocols
      ? new WebSocket(this.config.url, this.config.protocols)
      : new WebSocket(this.config.url);

    socket.addEventListener('open', () => {
      this.reconnectAttempt = 0;
      this.emitLifecycle('open');
    });

    socket.addEventListener('message', (event) => {
      try {
        const envelope = JSON.parse(event.data as string) as EvolutionEventEnvelope<TPayload>;
        for (const handler of this.envelopeHandlers) handler(envelope);
      } catch {
        // Malformed frame: ignore, do not crash the projection.
      }
    });

    socket.addEventListener('close', () => {
      this.socket = null;
      if (this.closedByUser) {
        this.emitLifecycle('closed');
        return;
      }
      this.emitLifecycle('reconnecting');
      this.scheduleReconnect();
    });

    socket.addEventListener('error', () => {
      // 'close' follows; reconnection handled there.
    });

    this.socket = socket;
  }

  private scheduleReconnect(): void {
    const max = this.config.maxReconnectDelayMs ?? 30_000;
    const base = Math.min(1000 * 2 ** this.reconnectAttempt, max);
    const jitter = Math.floor(Math.random() * 250);
    this.reconnectAttempt += 1;
    this.reconnectTimer = setTimeout(() => this.open(), base + jitter);
  }

  private emitLifecycle(state: StreamLifecycle): void {
    for (const handler of this.lifecycleHandlers) handler(state);
  }
}