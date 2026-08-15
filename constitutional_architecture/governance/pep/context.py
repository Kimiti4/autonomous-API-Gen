"""
Phase 28.1 — Evolution promotion context builder (Milestone 5B).

Builds the GovernanceEvaluationRequest for evolution-engine promotions at
the promotion boundary. Every field the evolution policies check is set
explicitly, so the PEP evaluates against the same context contract the
default policy packs expect.

Policy-relevant context fields (per default packs 002-006):
  environment        staging / production
  parent_isr_hash    the ISR revision this promotion builds on
  has_rollback_plan  bool — promotions without one are denied
  verification_status passed | failed | unknown
  simulation_status  passed | failed | unknown
  fitness_evaluation_id  evidence ref for the fitness evaluation
  mutation_type      e.g. refactor | feature | fix | migration
  audit_commitment   bool — the promotion accepts auditability
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from constitutional_architecture.governance.schemas import GovernanceEvaluationRequest

SUBJECT_TYPE_EVOLUTION_PROPOSAL = "EVOLUTION_PROPOSAL"
ACTION_PROMOTE = "PROMOTE"


class EvolutionContextBuilder:
    """Declarative builder for evolution promotion requests."""

    def __init__(
        self,
        *,
        proposal_id: str,
        proposal_version: str = "1.0",
        proposal_content_hash: str = "",
        actor=None,
        environment: str = "staging",
        parent_isr_hash: str = "",
        has_rollback_plan: bool = True,
        rollback_plan_ref: str = "",
        verification_status: str = "unknown",
        simulation_status: str = "unknown",
        fitness_evaluation_id: str = "",
        mutation_type: str = "feature",
        audit_commitment: bool = True,
        evidence_refs: Optional[List[str]] = None,
    ) -> None:
        self.proposal_id = proposal_id
        self.proposal_version = proposal_version
        self.proposal_content_hash = proposal_content_hash
        self.actor = actor
        self.environment = environment
        self.parent_isr_hash = parent_isr_hash
        self.has_rollback_plan = has_rollback_plan
        self.rollback_plan_ref = rollback_plan_ref
        self.verification_status = verification_status
        self.simulation_status = simulation_status
        self.fitness_evaluation_id = fitness_evaluation_id
        self.mutation_type = mutation_type
        self.audit_commitment = audit_commitment
        self.evidence_refs = list(evidence_refs or [])

    def with_evidence(self, *refs: str) -> "EvolutionContextBuilder":
        self.evidence_refs.extend(refs)
        return self

    def build(self) -> GovernanceEvaluationRequest:
        if self.actor is None:
            raise ValueError("actor is required; use pep.client.autonomous_agent()")
        return GovernanceEvaluationRequest(
            subject_type=SUBJECT_TYPE_EVOLUTION_PROPOSAL,
            subject_id=self.proposal_id,
            action=ACTION_PROMOTE,
            actor=self.actor,
            environment=self.environment,
            context={
                "environment": self.environment,
                "parent_isr_hash": self.parent_isr_hash,
                "has_rollback_plan": self.has_rollback_plan,
                "rollback_plan_ref": self.rollback_plan_ref,
                "verification_status": self.verification_status,
                "simulation_status": self.simulation_status,
                "fitness_evaluation_id": self.fitness_evaluation_id,
                "mutation_type": self.mutation_type,
                "audit_commitment": self.audit_commitment,
                "proposal_version": self.proposal_version,
                "proposal_content_hash": self.proposal_content_hash,
            },
            evidence_refs=self.evidence_refs,
        )
