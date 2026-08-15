"""
Production-feedback-aware evolution engine wrapper.

This wrapper can wrap:
- MultiCandidateEvolutionEngine
- CompilerAwareMultiCandidateEngine
- any engine exposing the same interface

It augments candidate fitness with production feedback evidence.
"""

from __future__ import annotations

from typing import Dict, Optional

from .feedback import (
    FeedbackEvaluationContext,
    FeedbackFitnessEvaluator,
    FeedbackFitnessPolicy,
    FeedbackFitnessReport,
    GenomeRefinementRecommendation,
    InMemorySignalStore,
    ProductionSignal,
)
from .models import FitnessEvaluation, ProposalStatus, utcnow
from .utils import deterministic_id


def merge_feedback_fitness(
    base_fitness: FitnessEvaluation,
    feedback_report: FeedbackFitnessReport,
    candidate_id: str,
) -> FitnessEvaluation:
    """Merge base fitness with production feedback fitness."""

    objectives = dict(base_fitness.objectives)
    constraints = dict(base_fitness.constraints)

    for objective_name, objective_value in feedback_report.objectives.items():
        objectives[f"feedback_{objective_name}"] = objective_value

    for constraint_name, constraint_value in feedback_report.constraints.items():
        constraints[f"feedback_{constraint_name}"] = constraint_value

    notes = list(base_fitness.notes)

    if not feedback_report.passed:
        notes.append("Production feedback fitness failed.")

    notes.extend(feedback_report.issues[:5])

    passed = base_fitness.passed and feedback_report.passed

    fitness_id = deterministic_id(
        "production_feedback_fitness",
        {
            "candidate_id": candidate_id,
            "objectives": objectives,
            "constraints": constraints,
        },
    )

    return FitnessEvaluation(
        id=fitness_id,
        candidate_id=candidate_id,
        objectives=objectives,
        constraints=constraints,
        passed=passed,
        notes=notes,
        created_at=utcnow().isoformat(),
    )


class ProductionFeedbackAwareEngine:
    """Wraps an evolution engine with production feedback fitness."""

    def __init__(
        self,
        inner_engine,
        signal_store: Optional[InMemorySignalStore] = None,
        policy: Optional[FeedbackFitnessPolicy] = None,
    ) -> None:
        self._inner = inner_engine
        self.base = inner_engine.base

        self.signal_store = signal_store or InMemorySignalStore()
        self.policy = policy or FeedbackFitnessPolicy()

        self.evaluator = FeedbackFitnessEvaluator(
            signal_store=self.signal_store,
            policy=self.policy,
        )

        self.feedback_reports: Dict[str, Dict[str, FeedbackFitnessReport]] = {}
        self.feedback_base_fitness: Dict[str, Dict[str, FitnessEvaluation]] = {}

    # ------------------------------------------------------------------
    # Proxy methods
    # ------------------------------------------------------------------

    def generate_candidates(self, proposal_id, request, actor_id):
        return self._inner.generate_candidates(proposal_id, request, actor_id)

    def evaluate_candidates(self, proposal_id, actor_id, force: bool = False):
        self._inner.evaluate_candidates(proposal_id, actor_id, force)

        self._augment_with_feedback(
            proposal_id=proposal_id,
            actor_id=actor_id,
            force=force,
        )

        return list(self._inner.evaluations.get(proposal_id, {}).values())

    def select_pareto(self, proposal_id, policy, actor_id):
        return self._inner.select_pareto(proposal_id, policy, actor_id)

    def get_evaluations(self, proposal_id):
        return self._inner.get_evaluations(proposal_id)

    def get_pareto_result(self, proposal_id):
        return self._inner.get_pareto_result(proposal_id)

    # ------------------------------------------------------------------
    # Feedback-specific methods
    # ------------------------------------------------------------------

    def add_signal(self, signal: ProductionSignal) -> ProductionSignal:
        return self.signal_store.add_signal(signal)

    def get_feedback_report(
        self,
        proposal_id: str,
        candidate_id: str,
    ) -> Optional[FeedbackFitnessReport]:
        self.base._get_proposal(proposal_id)

        return (
            self.feedback_reports
            .get(proposal_id, {})
            .get(candidate_id)
        )

    def get_genome_recommendations(
        self,
        proposal_id: str,
        candidate_id: str,
    ) -> list[GenomeRefinementRecommendation]:
        report = self.get_feedback_report(proposal_id, candidate_id)

        if not report:
            return []

        return report.recommendations

    # ------------------------------------------------------------------
    # Internal augmentation
    # ------------------------------------------------------------------

    def _augment_with_feedback(
        self,
        proposal_id: str,
        actor_id: str,
        force: bool,
    ) -> None:
        proposal = self.base._get_proposal(proposal_id)

        evaluations = self._inner.evaluations.get(proposal_id, {})

        reports = self.feedback_reports.setdefault(proposal_id, {})
        base_fitness_store = self.feedback_base_fitness.setdefault(proposal_id, {})

        for evaluation in evaluations.values():
            if not evaluation.fitness:
                continue

            if not evaluation.feasible:
                continue

            if evaluation.candidate_id in reports and not force:
                continue

            candidate = self.base.candidates.get(evaluation.candidate_id)

            if not candidate:
                continue

            context = FeedbackEvaluationContext(
                target_ref=proposal.request.target_ref,
                extra_subject_refs=[
                    proposal.id,
                    candidate.id,
                ],
            )

            feedback_report = self.evaluator.evaluate_candidate(
                candidate=candidate,
                context=context,
            )

            reports[evaluation.candidate_id] = feedback_report

            base_fitness = base_fitness_store.get(
                evaluation.candidate_id,
                evaluation.fitness,
            )

            base_fitness_store[evaluation.candidate_id] = base_fitness

            merged_fitness = merge_feedback_fitness(
                base_fitness=base_fitness,
                feedback_report=feedback_report,
                candidate_id=evaluation.candidate_id,
            )

            evaluation.fitness = merged_fitness

            if merged_fitness.passed:
                evaluation.feasible = True
            else:
                evaluation.feasible = False

                if "feedback_fitness_failed" not in evaluation.reasons:
                    evaluation.reasons.append("feedback_fitness_failed")

        all_evaluations = list(evaluations.values())

        any_feasible = any(
            evaluation.feasible
            for evaluation in all_evaluations
        )

        if any_feasible:
            proposal.status = ProposalStatus.EVALUATED
            proposal.error = None
        else:
            proposal.status = ProposalStatus.FAILED
            proposal.error = "No feasible production-feedback-aware candidates."

        proposal.updated_at = utcnow().isoformat()

        self.base.history.record(
            proposal_id=proposal_id,
            event_type="production_feedback_evaluation_completed",
            actor_id=actor_id,
            details={
                "candidate_count": len(all_evaluations),
                "feasible_count": sum(
                    1
                    for evaluation in all_evaluations
                    if evaluation.feasible
                ),
            },
        )
