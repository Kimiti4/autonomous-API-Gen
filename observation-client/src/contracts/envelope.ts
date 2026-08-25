/**
 * AM-2: eventType is a forward-compatible string. Known constants below.
 * Clients MUST tolerate unknown event types without failing.
 */
export type EventType = string;

export const EventTypes = {
  IsrUpdated: 'isr.updated',
  EvolutionStageChanged: 'evolution.stage_changed',
  FitnessEvaluated: 'fitness.evaluated',
  CandidatePromoted: 'candidate.promoted',
  GovernanceDecisionMade: 'governance.decision_made',
  OperationalFeedbackReceived: 'operational.feedback_received',
  ObservationError: 'observation.error',
  EventDropped: 'event.dropped',
  /** AM-1: additive liveness signal. */
  Heartbeat: 'observation.heartbeat',
} as const;

export interface EventSource {
  readonly subsystem: string;
  readonly revision: string;
}

export interface EventIntegrity {
  readonly contentHash: string;
  readonly signature?: string;
}

export interface EvolutionEventEnvelope<TPayload = unknown> {
  readonly eventId: string;
  readonly streamId: string;
  readonly sequence: number;
  readonly eventType: EventType;
  readonly occurredAt: string;
  readonly correlationId: string;
  readonly causationId?: string | null;
  readonly generation: number;
  readonly source: EventSource;
  readonly payload: TPayload;
  readonly integrity?: EventIntegrity;
}