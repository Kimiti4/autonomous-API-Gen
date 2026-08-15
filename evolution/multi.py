"""
Multi-candidate evolution engine.

This engine extends the Phase 21 evolution lifecycle with:
- multiple candidate generation
- per-candidate evaluation
- Pareto selection
- selected-candidate promotion support
"""

from __future__ import annotations

from typing import Dict, List

from .engine import SelfEvolutionEngine
from .errors import InvalidStateError
from .models import (
    CandidateArchitecture,
    CandidateEvaluationRecord,
    GenerateCandidatesRequest,
    MutationSpec,
    ParetoSelectionPolicy,
    ParetoSelectionResult,
    ProposalStatus,
    utcnow,
)
from .pareto import select_pareto
from .utils import canonical_json, deterministic_id, sha256_hex


TERMINAL_STATES = {
    ProposalStatus.APPROVED,
    ProposalStatus.PENDING_APPROVAL,
    ProposalStatus.REJECTED,
    ProposalStatus.PROMOTED,
    ProposalStatus.ROLLED_BACK,
}


class MultiCandidateEvolutionEngine:
    """Coordinates multi-candidate evolution on top of the base engine."""

    def __init__(self, base_engine: SelfEvolutionEngine) -> None:
        self.base = base_engine

        self.evaluations: Dict[str, Dict[str, CandidateEvaluationRecord]] = {}
        self.selections: Dict[str, ParetoSelectionResult] = {}

    # ------------------------------------------------------------------
    # Candidate generation
    # ------------------------------------------------------------------

    def generate_candidates(
        self,
        proposal_id: str,
        request: GenerateCandidatesRequest,
        actor_id: str,
    ) -> List[CandidateArchitecture]:
        """Generate multiple candidate architectures for a proposal."""

        proposal = self.base._get_proposal(proposal_id)

        if proposal.status in TERMINAL_STATES:
            raise InvalidStateError(
                "Cannot generate candidates for a proposal in a terminal state."
            )

        mutation_specs: List[MutationSpec] = []

        if request.include_base_mutation:
            mutation_specs.append(proposal.request.mutation)

        mutation_specs.extend(request.mutations)

        if not mutation_specs:
            raise InvalidStateError(
                "At least one mutation specification is required."
            )

        base_isr = proposal.request.base_isr

        base_isr_hash = sha256_hex(canonical_json(base_isr))

        created_candidates: List[CandidateArchitecture] = []

        for spec in mutation_specs:
            if not spec.id:
                spec.id = deterministic_id(
                    "mutation",
                    spec.model_dump(mode="json"),
                )

            mutated_isr = self.base.mutation_engine.apply(base_isr, spec)

            content_hash = sha256_hex(canonical_json(mutated_isr))

            candidate_id = deterministic_id(
                "candidate",
                {
                    "proposal_id": proposal_id,
                    "mutation_id": spec.id,
                    "content_hash": content_hash,
                },
            )

            existing_candidate = self.base.candidates.get(candidate_id)

            if existing_candidate:
                if candidate_id not in proposal.candidate_ids:
                    proposal.candidate_ids.append(candidate_id)

                created_candidates.append(existing_candidate)
                continue

            candidate = CandidateArchitecture(
                id=candidate_id,
                proposal_id=proposal_id,
                mutation_spec_id=spec.id,
                base_isr_hash=base_isr_hash,
                content_hash=content_hash,
                isr=mutated_isr,
                created_at=utcnow().isoformat(),
            )

            self.base.candidates[candidate_id] = candidate

            if candidate_id not in proposal.candidate_ids:
                proposal.candidate_ids.append(candidate_id)

            created_candidates.append(candidate)

        proposal.status = ProposalStatus.MUTATED
        proposal.selected_candidate_id = None
        proposal.error = None
        proposal.updated_at = utcnow().isoformat()

        self.base.history.record(
            proposal_id=proposal_id,
            event_type="multi_candidates_generated",
            actor_id=actor_id,
            details={
                "candidate_count": len(created_candidates),
                "candidate_ids": [
                    candidate.id for candidate in created_candidates
                ],
            },
        )

        return created_candidates

    # ------------------------------------------------------------------
    # Candidate evaluation
    # ------------------------------------------------------------------

    def evaluate_candidates(
        self,
        proposal_id: str,
        actor_id: str,
        force: bool = False,
    ) -> List[CandidateEvaluationRecord]:
        """Evaluate all candidates belonging to a proposal."""

        proposal = self.base._get_proposal(proposal_id)

        if not proposal.candidate_ids:
            raise InvalidStateError("Proposal has no candidates.")

        evaluations = self.evaluations.setdefault(proposal_id, {})

        for candidate_id in proposal.candidate_ids:
            if candidate_id in evaluations and not force:
                continue

            candidate = self.base.candidates.get(candidate_id)

            if not candidate:
                continue

            reasons: List[str] = []
            simulation = None
            verification = None
            fitness = None
            feasible = False

            try:
                simulation = self.base.simulator.simulate(candidate)

                self.base.simulations[simulation.id] = simulation

                if simulation.id not in proposal.simulation_ids:
                    proposal.simulation_ids.append(simulation.id)

                if simulation.status != "PASSED":
                    reasons.append("simulation_failed")
                else:
                    verification = self.base.verifier.verify(
                        candidate,
                        proposal,
                    )

                    if not verification.valid:
                        reasons.append("verification_failed")
                    else:
                        fitness = self.base.fitness_evaluator.evaluate(
                            candidate,
                            simulation,
                            verification,
                        )

                        if not fitness.passed:
                            reasons.append("fitness_failed")
                        else:
                            feasible = True

            except Exception as exc:
                reasons.append(str(exc))

            evaluations[candidate_id] = CandidateEvaluationRecord(
                candidate_id=candidate_id,
                simulation_id=simulation.id if simulation else None,
                verification=verification,
                fitness=fitness,
                feasible=feasible,
                reasons=reasons,
                created_at=utcnow().isoformat(),
            )

        all_evaluations = list(evaluations.values())

        any_feasible = any(
            evaluation.feasible for evaluation in all_evaluations
        )

        if any_feasible:
            proposal.status = ProposalStatus.EVALUATED
            proposal.error = None
        else:
            proposal.status = ProposalStatus.FAILED
            proposal.error = "No feasible candidates were produced."

        proposal.updated_at = utcnow().isoformat()

        self.base.history.record(
            proposal_id=proposal_id,
            event_type="multi_candidates_evaluated",
            actor_id=actor_id,
            details={
                "candidate_count": len(all_evaluations),
                "feasible_count": sum(
                    1 for evaluation in all_evaluations if evaluation.feasible
                ),
            },
        )

        return all_evaluations

    # ------------------------------------------------------------------
    # Pareto selection
    # ------------------------------------------------------------------

    def select_pareto(
        self,
        proposal_id: str,
        policy: ParetoSelectionPolicy,
        actor_id: str,
    ) -> ParetoSelectionResult:
        """Select preferred candidates using Pareto ranking."""

        proposal = self.base._get_proposal(proposal_id)

        evaluations = list(self.evaluations.get(proposal_id, {}).values())

        if not evaluations:
            raise InvalidStateError(
                "Candidates must be evaluated before Pareto selection."
            )

        result = select_pareto(
            proposal_id=proposal_id,
            evaluations=evaluations,
            policy=policy,
        )

        self.selections[proposal_id] = result

        if result.selected_candidate_id:
            proposal.selected_candidate_id = result.selected_candidate_id

            if result.selected_candidate_id in proposal.candidate_ids:
                proposal.candidate_ids.remove(result.selected_candidate_id)
                proposal.candidate_ids.append(result.selected_candidate_id)

            selected_evaluation = self.evaluations.get(
                proposal_id, {}
            ).get(result.selected_candidate_id)

            if selected_evaluation:
                if selected_evaluation.verification:
                    proposal.verification = selected_evaluation.verification

                if selected_evaluation.fitness:
                    proposal.fitness = selected_evaluation.fitness

        proposal.updated_at = utcnow().isoformat()

        self.base.history.record(
            proposal_id=proposal_id,
            event_type="pareto_selection_completed",
            actor_id=actor_id,
            details={
                "selected_candidate_id": result.selected_candidate_id,
                "selected_candidate_ids": result.selected_candidate_ids,
                "objectives": result.objectives,
            },
        )

        return result

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_evaluations(
        self,
        proposal_id: str,
    ) -> List[CandidateEvaluationRecord]:
        """Return evaluations for a proposal."""

        self.base._get_proposal(proposal_id)

        return list(self.evaluations.get(proposal_id, {}).values())

    def get_pareto_result(
        self,
        proposal_id: str,
    ) -> ParetoSelectionResult | None:
        """Return the Pareto selection result for a proposal."""

        self.base._get_proposal(proposal_id)

        return self.selections.get(proposal_id)
