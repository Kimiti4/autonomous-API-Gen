"""Run a counterfactual repair cycle through ESAP's normal downstream gates."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .candidate_measurements import CandidateMeasurementResult, execute_candidate_measurements, measurement_evidence_map
from .counterfactual_execution import CounterfactualExecutionResult, execute_counterfactual_work
from .counterfactual_work import CounterfactualWorkPlan
from .dependency_reexecution import DependencyExecutionResult, execute_dependent_reverification
from .evidence_scoring import DerivedArchitectureScore, derive_architecture_score
from .evolution_population import EvolutionMember
from .fullstack_genome import FullStackGenome
from .pareto_architecture import ArchitectureScore, Objective
from .rejection_analysis import RejectionRecord, record_rejection, derive_counterfactual_requirements
from .successor_admission import SuccessorAdmission, SuccessorEvent, admit_successor, materialize_successor_event
from .specialized_mutations import EngineeringMutationSpec
from .cross_domain_evolution import CoEvolutionResult


@dataclass(frozen=True)
class CounterfactualCycle:
    execution: CounterfactualExecutionResult
    dependency: DependencyExecutionResult
    measurements: CandidateMeasurementResult
    score: DerivedArchitectureScore
    successor: SuccessorEvent
    admission: SuccessorAdmission | None
    rejection: RejectionRecord | None


def execute_counterfactual_cycle(
    *,
    source: CoEvolutionResult,
    source_member: EvolutionMember,
    work: CounterfactualWorkPlan,
    genome: FullStackGenome,
    mutation_specs_by_objective: Mapping[str, EngineeringMutationSpec],
    contracts_by_objective: Mapping[str, tuple[Any, ...]],
    observations: Mapping[str, Any],
    dependency_graph: Mapping[str, Sequence[str]],
    dependent_specs: tuple[EngineeringMutationSpec, ...],
    verifiers: Mapping[str, Any],
    evidence_by_property: Mapping[str, tuple[str, ...]],
    objectives: tuple[Objective, ...],
    measurement_runners: Mapping[str, Any],
    measurement_context: Mapping[str, Any],
    event_id: str,
    successor_architecture_id: str,
    generation: int,
) -> CounterfactualCycle:
    execution = execute_counterfactual_work(
        work, genome, mutation_specs_by_objective,
        contracts_by_objective, observations,
    )
    if not execution.executions:
        raise ValueError("counterfactual-cycle-requires-execution")

    # Counterfactual mutations become ordinary ESAP repair executions only
    # after their own verification gates have passed.
    from .repair_coevolution import RepairCandidate, RepairExecution
    from .verification_plans import build_verification_plan, execute_verification

    repair_results = []
    for item in execution.executions:
        spec = mutation_specs_by_objective.get(item.objective)
        if spec is None:
            raise ValueError("counterfactual-cycle-missing-mutation:" + item.objective)
        plan = build_verification_plan(spec, verifiers)
        evidence_by_gate = {
            f"{spec.mutation.request.domain}:{prop}": tuple(
                evidence_by_property.get(prop, ())
            )
            for prop in spec.verification_properties
        }
        report = execute_verification(plan, observations, evidence_by_gate)
        if not report.passed:
            raise ValueError(
                "counterfactual-repair-verification-failed:" + item.objective
            )
        repair_results.append(
            RepairExecution(
                RepairCandidate(
                    source_mutation_id=item.work_id,
                    repair_mutation_id=item.mutation_id,
                    domain=spec.mutation.request.domain,
                    rationale=spec.mutation.request.rationale,
                    counterexample_properties=tuple(item.acceptance_properties),
                ),
                item.evaluation.genome,
                report,
            )
        )
    repair_results = tuple(repair_results)
    dependency = execute_dependent_reverification(
        source, repair_results, dependency_graph, dependent_specs,
        verifiers, observations, evidence_by_property,
        successor_architecture_id=successor_architecture_id,
    )
    measurements = execute_candidate_measurements(
        successor_architecture_id, dependency.final_architecture,
        objectives, measurement_runners, measurement_context,
    )
    score = derive_architecture_score(
        successor_architecture_id, repair_results, dependency,
        objectives, measurement_evidence=measurement_evidence_map(measurements),
    )
    successor = materialize_successor_event(
        source, dependency,
        event_id=event_id, source_member=source_member, score=score.score,
    )
    admission = None
    rejection = None
    try:
        admission = admit_successor(
            source_member, successor, score.score, objectives, generation,
        )
    except ValueError as exc:
        if str(exc) != "successor-dominated":
            raise
        rejection = record_rejection(
            score.score, reasons=("successor-dominated",),
            frontier_scores=(source_member.score,), objectives=objectives,
        )
    return CounterfactualCycle(
        execution, dependency, measurements, score, successor, admission, rejection,
    )
