"""
Compiler-aware multi-candidate evolution engine.

This engine extends Phase 21.1 multi-candidate evolution with
compiler-in-the-loop fitness evaluation.
"""

from __future__ import annotations

from typing import Dict

from .compiler_fitness import (
    CompilationFitnessReport,
    CompilerFitnessEvaluator,
    CompilerFitnessPolicy,
    CompilerGateway,
    merge_fitness,
)
from .models import FitnessEvaluation, ProposalStatus, utcnow
from .multi import MultiCandidateEvolutionEngine


class CompilerAwareMultiCandidateEngine(MultiCandidateEvolutionEngine):
    """Multi-candidate engine with compiler-in-the-loop evaluation."""

    def __init__(
        self,
        base_engine,
        compiler_gateway: CompilerGateway,
        policy: CompilerFitnessPolicy,
    ) -> None:
        super().__init__(base_engine)

        self.compiler_fitness = CompilerFitnessEvaluator(
            gateway=compiler_gateway,
            policy=policy,
        )

        self.compilation_reports: Dict[str, Dict[str, CompilationFitnessReport]] = {}
        self.base_fitness: Dict[str, Dict[str, FitnessEvaluation]] = {}

    def evaluate_candidates(
        self,
        proposal_id: str,
        actor_id: str,
        force: bool = False,
    ):
        """Evaluate candidates, including compiler-in-the-loop fitness."""

        evaluations = super().evaluate_candidates(
            proposal_id=proposal_id,
            actor_id=actor_id,
            force=force,
        )

        proposal = self.base._get_proposal(proposal_id)

        reports = self.compilation_reports.setdefault(proposal_id, {})
        base_fitness_store = self.base_fitness.setdefault(proposal_id, {})

        for evaluation in evaluations:
            if not evaluation.fitness:
                continue

            if not evaluation.feasible:
                continue

            if evaluation.candidate_id in reports and not force:
                continue

            candidate = self.base.candidates.get(evaluation.candidate_id)

            if not candidate:
                continue

            base_fitness = base_fitness_store.get(
                evaluation.candidate_id,
                evaluation.fitness,
            )

            base_fitness_store[evaluation.candidate_id] = base_fitness

            compilation_report = self.compiler_fitness.evaluate_candidate(
                candidate
            )

            reports[evaluation.candidate_id] = compilation_report

            merged_fitness = merge_fitness(
                base_fitness=base_fitness,
                compilation_report=compilation_report,
                candidate_id=evaluation.candidate_id,
            )

            evaluation.fitness = merged_fitness

            if merged_fitness.passed:
                evaluation.feasible = True
            else:
                evaluation.feasible = False

                if "compiler_fitness_failed" not in evaluation.reasons:
                    evaluation.reasons.append("compiler_fitness_failed")

        all_evaluations = list(
            self.evaluations.get(proposal_id, {}).values()
        )

        any_feasible = any(
            evaluation.feasible
            for evaluation in all_evaluations
        )

        if any_feasible:
            proposal.status = ProposalStatus.EVALUATED
            proposal.error = None
        else:
            proposal.status = ProposalStatus.FAILED
            proposal.error = "No feasible compiler-aware candidates."

        proposal.updated_at = utcnow().isoformat()

        self.base.history.record(
            proposal_id=proposal_id,
            event_type="compiler_in_the_loop_evaluation_completed",
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

        return all_evaluations

    def get_compilation_report(
        self,
        proposal_id: str,
        candidate_id: str,
    ) -> CompilationFitnessReport | None:
        """Return the compiler fitness report for a candidate."""

        self.base._get_proposal(proposal_id)

        return (
            self.compilation_reports
            .get(proposal_id, {})
            .get(candidate_id)
        )
