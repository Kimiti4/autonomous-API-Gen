"""
Self-Evolution Engine kernel.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from .errors import (
    InvalidStateError,
    MutationError,
    ProposalNotFoundError,
)
from .fitness import FitnessEvaluator
from .governance_fitness_evaluator import GovernanceAwareFitnessEvaluator
from .governance import EvolutionGovernanceClient
from .history import EvolutionHistoryRepository
from .models import (
    ApprovalRecord,
    CandidateArchitecture,
    EvolutionProposal,
    EvolutionProposalRequest,
    EvolutionTargetType,
    GovernanceDecision,
    PromotionRecord,
    ProposalStatus,
    RollbackPlan,
    utcnow,
)
from .mutation import MutationEngine
from .simulation import ArchitectureSimulator
from .utils import canonical_json, deterministic_id, sha256_hex
from .verification import ConstitutionalVerifier


HIGH_IMPACT_TARGETS = {
    EvolutionTargetType.PLATFORM_CORE,
    EvolutionTargetType.COMPILER_PIPELINE,
    EvolutionTargetType.ISR_SCHEMA,
}


class EvolutionPolicy(BaseModel):
    """Policy controlling evolution behavior."""

    require_governance_for_high_impact: bool = True
    require_approval_for_high_impact: bool = True
    require_approval_for_platform_core: bool = True

    auto_approve_when_governance_allow: bool = True


class SelfEvolutionEngine:
    """Coordinates the full evolution lifecycle."""

    def __init__(
        self,
        mutation_engine: Optional[MutationEngine] = None,
        simulator: Optional[ArchitectureSimulator] = None,
        verifier: Optional[ConstitutionalVerifier] = None,
        fitness_evaluator: Optional[FitnessEvaluator] = None,
        governance_client: Optional[EvolutionGovernanceClient] = None,
        history: Optional[EvolutionHistoryRepository] = None,
        policy: Optional[EvolutionPolicy] = None,
    ) -> None:
        self.mutation_engine = mutation_engine or MutationEngine()
        self.simulator = simulator or ArchitectureSimulator()
        self.verifier = verifier or ConstitutionalVerifier()
        self.fitness_evaluator = fitness_evaluator or GovernanceAwareFitnessEvaluator()
        self.governance_client = governance_client
        self.history = history or EvolutionHistoryRepository()
        self.policy = policy or EvolutionPolicy()

        self.proposals: dict[str, EvolutionProposal] = {}
        self.candidates: dict[str, CandidateArchitecture] = {}
        self.simulations: dict[str, object] = {}
        self.promotions: dict[str, PromotionRecord] = {}

    # ------------------------------------------------------------------
    # Proposal lifecycle
    # ------------------------------------------------------------------

    def propose(
        self,
        request: EvolutionProposalRequest,
        actor_id: str,
    ) -> EvolutionProposal:
        created_at = utcnow().isoformat()

        if not request.mutation.id:
            request.mutation.id = deterministic_id(
                "mutation",
                request.mutation.model_dump(mode="json"),
            )

        base_isr_hash = sha256_hex(canonical_json(request.base_isr))

        proposal_id = deterministic_id(
            "evolution_proposal",
            {
                "title": request.title,
                "target_type": request.target_type.value,
                "target_ref": request.target_ref,
                "base_isr_hash": base_isr_hash,
                "mutation_id": request.mutation.id,
                "created_at": created_at,
            },
        )

        proposal = EvolutionProposal(
            id=proposal_id,
            status=ProposalStatus.DRAFT,
            request=request,
            created_at=created_at,
            updated_at=created_at,
        )

        self.proposals[proposal_id] = proposal

        self.history.record(
            proposal_id=proposal_id,
            event_type="proposal_created",
            actor_id=actor_id,
            details={
                "title": request.title,
                "target_type": request.target_type.value,
            },
        )

        return proposal

    def mutate(
        self,
        proposal_id: str,
        actor_id: str,
    ) -> CandidateArchitecture:
        proposal = self._get_proposal(proposal_id)

        if proposal.status not in {
            ProposalStatus.DRAFT,
            ProposalStatus.FAILED,
        }:
            raise InvalidStateError(
                "Mutation is only allowed for DRAFT or FAILED proposals."
            )

        try:
            mutated_isr = self.mutation_engine.apply(
                proposal.request.base_isr,
                proposal.request.mutation,
            )
        except MutationError as exc:
            proposal.status = ProposalStatus.FAILED
            proposal.error = str(exc)
            proposal.updated_at = utcnow().isoformat()

            self.history.record(
                proposal_id=proposal_id,
                event_type="mutation_failed",
                actor_id=actor_id,
                details={"error": str(exc)},
            )

            raise

        base_isr_hash = sha256_hex(
            canonical_json(proposal.request.base_isr)
        )

        content_hash = sha256_hex(canonical_json(mutated_isr))

        candidate_id = deterministic_id(
            "candidate",
            {
                "proposal_id": proposal_id,
                "mutation_id": proposal.request.mutation.id,
                "content_hash": content_hash,
            },
        )

        candidate = CandidateArchitecture(
            id=candidate_id,
            proposal_id=proposal_id,
            mutation_spec_id=proposal.request.mutation.id,
            base_isr_hash=base_isr_hash,
            content_hash=content_hash,
            isr=mutated_isr,
            created_at=utcnow().isoformat(),
        )

        self.candidates[candidate_id] = candidate

        proposal.candidate_ids.append(candidate_id)
        proposal.status = ProposalStatus.MUTATED
        proposal.error = None
        proposal.updated_at = utcnow().isoformat()

        self.history.record(
            proposal_id=proposal_id,
            event_type="candidate_mutated",
            actor_id=actor_id,
            details={
                "candidate_id": candidate_id,
            },
        )

        return candidate

    def simulate(
        self,
        proposal_id: str,
        actor_id: str,
    ):
        proposal = self._get_proposal(proposal_id)

        if proposal.status != ProposalStatus.MUTATED:
            raise InvalidStateError(
                "Simulation is only allowed after mutation."
            )

        candidate = self._latest_candidate(proposal)

        simulation = self.simulator.simulate(candidate)

        self.simulations[simulation.id] = simulation
        proposal.simulation_ids.append(simulation.id)

        if simulation.status == "FAILED":
            proposal.status = ProposalStatus.FAILED
            proposal.error = "Architecture simulation failed."
        else:
            proposal.status = ProposalStatus.SIMULATED
            proposal.error = None

        proposal.updated_at = utcnow().isoformat()

        self.history.record(
            proposal_id=proposal_id,
            event_type="simulation_completed",
            actor_id=actor_id,
            details={
                "simulation_id": simulation.id,
                "status": simulation.status,
            },
        )

        return simulation

    def verify(
        self,
        proposal_id: str,
        actor_id: str,
    ):
        proposal = self._get_proposal(proposal_id)

        if proposal.status != ProposalStatus.SIMULATED:
            raise InvalidStateError(
                "Verification is only allowed after successful simulation."
            )

        candidate = self._latest_candidate(proposal)

        verification = self.verifier.verify(candidate, proposal)

        proposal.verification = verification

        if not verification.valid:
            proposal.status = ProposalStatus.FAILED
            proposal.error = "Verification failed."
        else:
            proposal.status = ProposalStatus.VERIFIED
            proposal.error = None

        proposal.updated_at = utcnow().isoformat()

        self.history.record(
            proposal_id=proposal_id,
            event_type="verification_completed",
            actor_id=actor_id,
            details={
                "valid": verification.valid,
            },
        )

        return verification

    def evaluate_fitness(
        self,
        proposal_id: str,
        actor_id: str,
    ):
        proposal = self._get_proposal(proposal_id)

        if proposal.status != ProposalStatus.VERIFIED:
            raise InvalidStateError(
                "Fitness evaluation is only allowed after verification."
            )

        candidate = self._latest_candidate(proposal)
        simulation = self._latest_simulation(proposal)

        fitness = self.fitness_evaluator.evaluate(
            candidate,
            simulation,
            proposal.verification,
        )

        proposal.fitness = fitness

        if not fitness.passed:
            proposal.status = ProposalStatus.FAILED
            proposal.error = "Fitness constraints were not satisfied."
        else:
            proposal.status = ProposalStatus.EVALUATED
            proposal.error = None

        proposal.updated_at = utcnow().isoformat()

        self.history.record(
            proposal_id=proposal_id,
            event_type="fitness_evaluated",
            actor_id=actor_id,
            details={
                "fitness_id": fitness.id,
                "passed": fitness.passed,
            },
        )

        return fitness

    def submit_for_approval(
        self,
        proposal_id: str,
        actor_id: str,
    ) -> EvolutionProposal:
        proposal = self._get_proposal(proposal_id)

        if proposal.status != ProposalStatus.EVALUATED:
            raise InvalidStateError(
                "Approval submission is only allowed after fitness evaluation."
            )

        high_impact = (
            proposal.request.high_impact
            or proposal.request.target_type in HIGH_IMPACT_TARGETS
        )

        context = {
            "proposal_id": proposal.id,
            "title": proposal.request.title,
            "target_type": proposal.request.target_type.value,
            "target_ref": proposal.request.target_ref,
            "high_impact": high_impact,
            "fitness": proposal.fitness.model_dump(mode="json")
            if proposal.fitness
            else None,
            "verification": proposal.verification.model_dump(mode="json")
            if proposal.verification
            else None,
        }

        if self.governance_client:
            decision = self.governance_client.evaluate(proposal, context)
        else:
            if high_impact and self.policy.require_governance_for_high_impact:
                decision = GovernanceDecision(
                    decision="DENY",
                    reason=(
                        "Governance client is unavailable for high-impact "
                        "evolution."
                    ),
                )
            else:
                decision = GovernanceDecision(
                    decision="ALLOW",
                    reason="Governance client is not configured.",
                )

        proposal.governance_decision = decision

        if decision.decision == "DENY":
            proposal.status = ProposalStatus.REJECTED
            proposal.error = decision.reason

        elif decision.decision == "REQUIRE_APPROVAL":
            proposal.status = ProposalStatus.PENDING_APPROVAL

        else:
            forced_approval = high_impact and (
                self.policy.require_approval_for_high_impact
                or (
                    proposal.request.target_type
                    == EvolutionTargetType.PLATFORM_CORE
                    and self.policy.require_approval_for_platform_core
                )
            )

            if forced_approval:
                proposal.status = ProposalStatus.PENDING_APPROVAL
            elif self.policy.auto_approve_when_governance_allow:
                proposal.status = ProposalStatus.APPROVED
            else:
                proposal.status = ProposalStatus.PENDING_APPROVAL

        proposal.updated_at = utcnow().isoformat()

        self.history.record(
            proposal_id=proposal_id,
            event_type="approval_submitted",
            actor_id=actor_id,
            details={
                "decision": decision.decision,
                "status": proposal.status.value,
            },
        )

        return proposal

    def approve(
        self,
        proposal_id: str,
        approver_id: str,
        decision: str,
        comments: str = "",
    ) -> EvolutionProposal:
        proposal = self._get_proposal(proposal_id)

        if proposal.status != ProposalStatus.PENDING_APPROVAL:
            raise InvalidStateError(
                "Approval is only allowed for PENDING_APPROVAL proposals."
            )

        if decision not in {"APPROVED", "REJECTED"}:
            raise InvalidStateError(
                "Approval decision must be APPROVED or REJECTED."
            )

        approval = ApprovalRecord(
            approver_id=approver_id,
            decision=decision,
            comments=comments,
            created_at=utcnow().isoformat(),
        )

        proposal.approval = approval

        if decision == "APPROVED":
            proposal.status = ProposalStatus.APPROVED
            proposal.error = None
        else:
            proposal.status = ProposalStatus.REJECTED
            proposal.error = comments or "Proposal rejected by approver."

        proposal.updated_at = utcnow().isoformat()

        self.history.record(
            proposal_id=proposal_id,
            event_type="approval_decided",
            actor_id=approver_id,
            details={
                "decision": decision,
            },
        )

        return proposal

    def promote(
        self,
        proposal_id: str,
        environment: str,
        actor_id: str,
    ) -> PromotionRecord:
        proposal = self._get_proposal(proposal_id)

        if proposal.status != ProposalStatus.APPROVED:
            raise InvalidStateError(
                "Promotion is only allowed for APPROVED proposals."
            )

        if not proposal.verification or not proposal.verification.valid:
            raise InvalidStateError(
                "Cannot promote without valid verification."
            )

        if not proposal.fitness or not proposal.fitness.passed:
            raise InvalidStateError(
                "Cannot promote without passing fitness evaluation."
            )

        candidate = self._latest_candidate(proposal)

        rollback_plan = RollbackPlan(
            parent_isr_hash=candidate.base_isr_hash,
            steps=[
                "Restore parent ISR hash as authoritative ISR.",
                "Mark promoted candidate as rolled back.",
                "Emit rollback audit event.",
                "Notify governed systems.",
            ],
            automated=False,
        )

        promotion_id = deterministic_id(
            "promotion",
            {
                "proposal_id": proposal_id,
                "candidate_id": candidate.id,
                "environment": environment,
            },
        )

        promotion = PromotionRecord(
            id=promotion_id,
            proposal_id=proposal_id,
            candidate_id=candidate.id,
            environment=environment,
            promoted_content_hash=candidate.content_hash,
            rollback_plan=rollback_plan,
            created_at=utcnow().isoformat(),
        )

        self.promotions[promotion_id] = promotion

        proposal.promotion = promotion
        proposal.status = ProposalStatus.PROMOTED
        proposal.updated_at = utcnow().isoformat()

        self.history.record(
            proposal_id=proposal_id,
            event_type="promotion_completed",
            actor_id=actor_id,
            details={
                "promotion_id": promotion_id,
                "environment": environment,
            },
        )

        return promotion

    def rollback(
        self,
        promotion_id: str,
        reason: str,
        actor_id: str,
    ) -> PromotionRecord:
        promotion = self.promotions.get(promotion_id)

        if not promotion:
            raise ProposalNotFoundError(
                f"Promotion not found: {promotion_id}"
            )

        if promotion.status != "ACTIVE":
            raise InvalidStateError(
                "Only active promotions can be rolled back."
            )

        promotion.status = "ROLLED_BACK"
        promotion.rolled_back_at = utcnow().isoformat()
        promotion.rollback_reason = reason

        proposal = self.proposals.get(promotion.proposal_id)

        if proposal:
            proposal.status = ProposalStatus.ROLLED_BACK
            proposal.updated_at = utcnow().isoformat()

            self.history.record(
                proposal_id=proposal.id,
                event_type="rollback_completed",
                actor_id=actor_id,
                details={
                    "promotion_id": promotion_id,
                    "reason": reason,
                },
            )

        return promotion

    def metrics(self) -> dict:
        status_counts: dict[str, int] = {}

        for proposal in self.proposals.values():
            status_counts[proposal.status.value] = (
                status_counts.get(proposal.status.value, 0) + 1
            )

        return {
            "proposal_count": len(self.proposals),
            "candidate_count": len(self.candidates),
            "simulation_count": len(self.simulations),
            "promotion_count": len(self.promotions),
            "status_counts": status_counts,
            "history_event_count": len(self.history.events),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_proposal(self, proposal_id: str) -> EvolutionProposal:
        proposal = self.proposals.get(proposal_id)

        if not proposal:
            raise ProposalNotFoundError(
                f"Evolution proposal not found: {proposal_id}"
            )

        return proposal

    def _latest_candidate(
        self,
        proposal: EvolutionProposal,
    ) -> CandidateArchitecture:
        selected_candidate_id = getattr(
            proposal,
            "selected_candidate_id",
            None,
        )

        if selected_candidate_id:
            candidate = self.candidates.get(selected_candidate_id)

            if candidate:
                return candidate

        if not proposal.candidate_ids:
            raise InvalidStateError("Proposal has no candidates.")

        candidate_id = proposal.candidate_ids[-1]
        candidate = self.candidates.get(candidate_id)

        if not candidate:
            raise InvalidStateError(
                f"Candidate not found: {candidate_id}"
            )

        return candidate

    def _latest_simulation(self, proposal: EvolutionProposal):
        if not proposal.simulation_ids:
            raise InvalidStateError("Proposal has no simulations.")

        simulation_id = proposal.simulation_ids[-1]
        simulation = self.simulations.get(simulation_id)

        if not simulation:
            raise InvalidStateError(
                f"Simulation not found: {simulation_id}"
            )

        return simulation
