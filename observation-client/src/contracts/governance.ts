export interface GovernanceProjection {
  readonly council: { members: ReadonlyArray<{ memberId: string; name: string; role: string; votingWeight: number }> };
  readonly decisions: ReadonlyArray<GovernanceDecision>;
  readonly gates: ReadonlyArray<{ gateId: string }>;
}
export interface GovernanceDecision {
  readonly decisionId: string;
  readonly candidateId: string;
  readonly generation: number;
  readonly verdict: string;
  readonly fromState: string;
  readonly toState: string;
  readonly authorizesTransition: boolean;
  readonly decidedBy: ReadonlyArray<string>;
  readonly rationale: string;
  readonly supersedesDecisionId: string | null;
  readonly evidenceRefs: ReadonlyArray<string>;
  readonly decidedAt: string;
}

/** Per-candidate governance history (platform: /governance/candidate). */
export interface CandidateGovernanceProjection {
  readonly candidateId: string;
  readonly decisions: ReadonlyArray<GovernanceDecision>;
}
