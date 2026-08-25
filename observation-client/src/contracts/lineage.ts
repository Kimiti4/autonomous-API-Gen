/**
 * Candidate lineage — TypeScript mirror of the platform's
 * app/core/contracts/lineage.py (top-level field set is parity-gated by
 * Gate 1; element shapes mirror the platform's lineage submodels).
 */
export interface OriginSpecView {
  readonly operationType: string;
  readonly parentCandidateIds: ReadonlyArray<string>;
  readonly operationId: string;
  readonly summary: string;
}

export interface EvolutionOperationView {
  readonly operationId: string;
  readonly operationType: string;
  readonly generation: number;
  readonly summary: string;
  readonly occurredAt: string;
}

export interface FitnessEvaluationView {
  readonly evaluationId: string;
  readonly generation: number;
  readonly fitnessScore: number;
  readonly objectiveScores: Readonly<Record<string, number>>;
  readonly evaluatedAt: string;
}

export interface VerificationView {
  readonly verificationId: string;
  readonly verifiedBy: string;
  readonly verdict: string;
  readonly evidenceRefs: ReadonlyArray<string>;
  readonly verifiedAt: string;
}

export interface DeploymentView {
  readonly deploymentId: string;
  readonly target: string;
  readonly deployedBy: string;
  readonly deployedAt: string;
}

export interface OperationalFeedbackView {
  readonly feedbackId: string;
  readonly source: string;
  readonly summary: string;
  readonly influencedNextGeneration: boolean;
  readonly receivedAt: string;
}

export interface CandidateLineage {
  readonly candidateId: string;
  readonly generation: number;
  readonly isrRevision: string;
  readonly requirementIds: ReadonlyArray<string>;
  readonly origin: OriginSpecView | null;
  readonly operations: ReadonlyArray<EvolutionOperationView>;
  readonly evaluations: ReadonlyArray<FitnessEvaluationView>;
  readonly verifications: ReadonlyArray<VerificationView>;
  readonly deployments: ReadonlyArray<DeploymentView>;
  readonly feedback: ReadonlyArray<OperationalFeedbackView>;
}
